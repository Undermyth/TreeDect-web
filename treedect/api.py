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
import logging

from utils import *

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
    logging.info("prefilling complete")

    masks = []
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        for j in range(point_grid.shape[1]):
            for i in range(point_grid.shape[0]):
                point_coord = np.expand_dims(point_grid[i, j], axis=0)
                point_label = np.array([1])
                current_masks, _, _ = predictor.predict(point_coords=point_coord, point_labels=point_label)
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
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)