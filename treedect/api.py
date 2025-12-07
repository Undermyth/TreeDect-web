from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sam2.sam2_image_predictor import SAM2ImagePredictor
from sam2.build_sam import build_sam2
from transformers import AutoImageProcessor, AutoModel
import base64
import uvicorn
import cv2
import numpy as np
import io
import gzip
import torch
from pydantic import BaseModel
import logging
from torch.utils.data import DataLoader
from sklearn.cluster import KMeans

from utils import *
from feature import FeatureExtractionDataset
import time
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, normalize
import umap

# ------------------------------------------------------------
# global states
# ------------------------------------------------------------
predictor = None
preprocessor = None
extractor = None
img = None

def load_model(model_name = "facebook/sam2-hiera-small"):
    global predictor
    predictor = SAM2ImagePredictor.from_pretrained("facebook/sam2-hiera-small", local_files_only=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    predictor.model.to(device)

def load_feature_extractor(model_name = "facebook/dinov2-small"):
    global preprocessor, extractor
    preprocessor = AutoImageProcessor.from_pretrained(model_name, local_files_only=True, use_fast=True)
    extractor = AutoModel.from_pretrained(model_name, local_files_only=True)


load_model()
load_feature_extractor()

app = FastAPI()

# 添加CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/load_image")
async def load_image(file: UploadFile = File(...)):
    global img
    try:
        # 读取上传的文件内容
        contents = await file.read()
        
        # 将文件内容转换为 numpy 数组
        nparr = np.frombuffer(contents, np.uint8)
        
        # 使用 cv2 解码图像
        img_cv2 = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 转换为 RGB 格式
        img = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
        
        # 检查图像是否成功加载
        if img is None:
            return JSONResponse(content={"error": "图像加载失败"}, status_code=400)
        
        # 返回成功信息
        return JSONResponse(content={"message": "图像加载成功", "height": img.shape[0], "width": img.shape[1]})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

class SegmentationRequest(BaseModel):
    row_sample_interval: int
    col_sample_interval: int
    overlap_ratio: float

@app.post("/generate_segmentation")
async def generate_segmentation(request: SegmentationRequest):
    row_sample_interval = request.row_sample_interval
    col_sample_interval = request.col_sample_interval
    overlap_ratio = request.overlap_ratio
    global img
    
    if img is None:
        return JSONResponse(content={"error": "No image loaded"}, status_code=400)

    height, width = img.shape[:2]
    point_grid = generation_sample_grid(height, width, row_sample_interval, col_sample_interval)
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        predictor.set_image(img)
    logging.info("prefilling complete")

    masks = []
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        for j in range(point_grid.shape[1]):
            for i in range(point_grid.shape[0]):
                point_coord = np.expand_dims(point_grid[i, j], axis=0)
                point_label = np.array([1])
                current_masks, _, _ = predictor.predict(point_coords=point_coord, point_labels=point_label, multimask_output=True)
                masks.append(current_masks[0].astype(bool))
    logging.info("prediction complete")
    
    filtered_grids, filtered_masks = filter_overlap_segments(point_grid, masks, height, width, overlap_ratio)
    logging.info("filter complete")

    num_masks = len(filtered_masks)
    
    palette = masks_to_palette(filtered_masks, height, width)

    # 使用gzip压缩数据而不是np.save
    buffer = io.BytesIO()
    # 将palette数据以原始二进制形式写入缓冲区
    palette_bytes = palette.tobytes()
    # 使用gzip压缩
    compressed_data = gzip.compress(palette_bytes)
    # 进行base64编码
    palette_base64 = base64.b64encode(compressed_data).decode('utf-8')
    
    return JSONResponse(content={
        "palette": palette_base64,
        "num_masks": num_masks,
        "height": height,
        "width": width
    })

class PointSegmentRequest(BaseModel):
    x: int
    y: int

@app.post("/point_segment")
def point_segment(request: PointSegmentRequest):
    x = request.x
    y = request.y
    point_coord = np.array([[x, y]]) 
    point_label = np.array([1])
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        current_masks, _, _ = predictor.predict(point_coords=point_coord, point_labels=point_label)
    mask = current_masks[0].astype(np.int32)
    buffer = io.BytesIO()
    mask_bytes = mask.tobytes()
    compressed_data = gzip.compress(mask_bytes)
    mask_base64 = base64.b64encode(compressed_data).decode('utf-8')
    height, width = img.shape[:2]

    return JSONResponse(content={
        "mask": mask_base64,
        "height": height,
        "width": width
    })

class ClusterRequest(BaseModel):
    palette: list
    k: int

@app.post("/cluster")
def cluster(request: ClusterRequest):
    # 将传入的二维列表转换为numpy数组
    palette = np.array(request.palette, dtype=np.int32)
    n_patch = 224 / extractor.config.patch_size
    dataset = FeatureExtractionDataset(palette, img, n_patch)
    loader = DataLoader(dataset, batch_size=128, shuffle=False, collate_fn=FeatureExtractionDataset.collate_fn)
    
    start_time = time.time()
    
    cls_tokens = []
    for i, batch in enumerate(loader):
        inputs = preprocessor(
            images=batch['data'],
            return_tensors="pt",
            size={"height": 224, "width": 224},   # 直接 resize 到 224x224
            crop_size=None,                       # 禁用 center crop
            do_center_crop=False
        )
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            outputs = extractor(**inputs)
        for hidden_state, block_mask in zip(outputs.last_hidden_state, batch['block_mask']):  # iteration over samples in batch
            patch_states = hidden_state[1:]
            valid_patchs = []
            for block_index in block_mask:
                valid_patchs.append(patch_states[block_index])
            if len(valid_patchs) == 0:
                valid_patchs.append(torch.zeros((768,)))   # empty patch
            cls_token = torch.stack(valid_patchs, dim=0).mean(dim=0)
            cls_tokens.append(cls_token.numpy())
    
    end_time = time.time()
    logging.info(f"Feature extraction took {end_time - start_time:.2f} seconds")

    # filter invalid (deleted) segments
    features = []
    indexes = []
    for i, (valid, cls_token) in enumerate(zip(dataset.valid, cls_tokens)):
        if valid:
            features.append((cls_token, dataset.mean_color[i], dataset.std_color[i], dataset.area[i]))
            indexes.append(i)

    # PCA on texture features from DINOv2
    # [VARI] does it need normalization?
    texture_features = np.stack([feature[0] for feature in features], axis=0)
    pca = PCA(n_components=7)
    texture_features = pca.fit_transform(texture_features)
    texture_features = normalize(texture_features, norm='l2')

    # manual features
    manual_features = np.stack([np.concat([feature[1], feature[2], np.array([feature[3]])], axis=-1) for feature in features], axis=0)
    features = np.concat([texture_features, manual_features], axis=-1)

    # normalization & UMAP
    scaler = StandardScaler()
    features = scaler.fit_transform(features)
    reducer = umap.UMAP(n_neighbors=30, min_dist=0.0, n_components=3, random_state=42)
    features = reducer.fit_transform(features)

    # # 将特征向量转换为numpy数组用于聚类
    # features = torch.stack(features).cpu().numpy()
    
    # 执行K-means聚类
    start_time = time.time()
    kmeans = KMeans(n_clusters=request.k, random_state=0)
    cluster_labels = kmeans.fit_predict(features)
    end_time = time.time()
    logging.info(f"K-means clustering took {end_time - start_time:.2f} seconds")

    labels = [-1 for _ in range(len(cls_tokens))]
    for index, cluster_label in zip(indexes, cluster_labels):
        labels[int(index)] = cluster_label
    cluster_labels = np.array(labels)

    areas = np.zeros(cluster_labels.max() + 1)
    for label, area in zip(cluster_labels, dataset.area):
        if label != -1:
            areas[label] += area

    position_x = np.round((dataset.bbox_top + dataset.bbox_bottom) / 2)
    position_y = np.round((dataset.bbox_left + dataset.bbox_right) / 2)
    # 返回聚类结果
    return JSONResponse(content={
        "labels": cluster_labels.tolist(),      # List[n_segments]. each element is the cluster label to the segment, start from 0, -1 for deleted segments
        "areas": areas.tolist(),                # List[n_clusters]. each element is the area in pixels to the cluster
        "position_x": position_x.tolist(),
        "position_y": position_y.tolist(),
    })
    

    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)