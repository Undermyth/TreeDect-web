from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sam2.sam2_image_predictor import SAM2ImagePredictor
from sam2.build_sam import build_sam2
import base64
import uvicorn
import cv2
import numpy as np
import io
import gzip
import torch
from pydantic import BaseModel

from utils import generation_sample_grid

# ------------------------------------------------------------
# global states
# ------------------------------------------------------------
predictor = None
img = None

def load_model(model_name = "facebook/sam2-hiera-large"):
    global predictor
    predictor = SAM2ImagePredictor.from_pretrained("facebook/sam2-hiera-large", local_files_only=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    predictor.model.to(device)

load_model()

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
async def load_image():
    global img
    try:
        # 读取example.jpg文件并进行base64编码
        with open("example.jpg", "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        img = cv2.imread("example.jpg")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # 返回base64编码的图像
        return JSONResponse(content={"image": encoded_string})
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

    masks = []
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        for j in range(point_grid.shape[1]):
            for i in range(point_grid.shape[0]):
                point_coord = np.expand_dims(point_grid[i, j], axis=0)
                point_label = np.array([1])
                current_masks, _, _ = predictor.predict(point_coords=point_coord, point_labels=point_label)
                masks.append(current_masks[0].astype(bool))
    
    def is_overlap(mask_a: np.ndarray, mask_b: np.ndarray, overlap_ratio: float) -> bool:
        overlap_mask = mask_a.astype(bool) & mask_b.astype(bool)
        ratio = overlap_mask.sum() / mask_b.sum()
        return ratio >= overlap_ratio
    
    filtered_masks = []
    legal_sample_points = []
    masks = np.stack(masks, axis=0)
    masks = masks.reshape(point_grid.shape[1], point_grid.shape[0], height, width)
    segment_mask = np.zeros((height, width))

    for i in range(masks.shape[0]):
        for j in range(masks.shape[1]):

            if is_overlap(segment_mask, masks[i, j], overlap_ratio):
                print(i, j)
                segment_mask = segment_mask.astype(bool) | masks[i, j].astype(bool)
                continue

            filtered_masks.append(masks[i, j])
            legal_sample_points.append(point_grid[j, i].tolist())  # 转换为列表以便JSON序列化
            segment_mask = segment_mask.astype(bool) | masks[i, j].astype(bool)
    
    # 处理mask返回格式
    encoded_masks = []
    for mask in filtered_masks:
        # 将bool数组压缩
        mask_bytes = np.packbits(mask.flatten()).tobytes()
        # 使用gzip进一步压缩
        compressed_mask = gzip.compress(mask_bytes)
        # base64编码以便传输
        encoded_mask = base64.b64encode(compressed_mask).decode('utf-8')
        encoded_masks.append(encoded_mask)
    
    # 将legal_sample_points转换为可序列化的格式
    sample_points_serializable = [point for point in legal_sample_points]
    
    return JSONResponse(content={
        "masks": encoded_masks,
        "sample_points": sample_points_serializable,
        "image_shape": [height, width]
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)