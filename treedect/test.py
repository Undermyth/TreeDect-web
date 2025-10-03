import torch
from sam2.sam2_image_predictor import SAM2ImagePredictor
import cv2
import numpy as np

ROW_SAMPLE_INTERVAL = 50
COL_SAMPLE_INTERVAL = 50
FILTER_OVERLAP_RATIO = 0.3

# ----------------------------------------------------------------
# 图像读取和采样点生成
# ----------------------------------------------------------------
# 读取图片
image = cv2.imread("example.jpg")
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
height, width = image.shape[:2]
# 生成点阵坐标
x_coords = np.arange(0, width, ROW_SAMPLE_INTERVAL)
y_coords = np.arange(0, height, COL_SAMPLE_INTERVAL)

# 计算padding
x_pad = (width - 1 - x_coords[-1]) // 2
y_pad = (height - 1 - y_coords[-1]) // 2

# 调整坐标以包含padding
x_coords = x_coords + x_pad
y_coords = y_coords + y_pad

# 确保坐标不会超出图像边界
x_coords = x_coords[x_coords < width]
y_coords = y_coords[y_coords < height]

# 生成网格点
x_grid, y_grid = np.meshgrid(x_coords, y_coords)
point_grid = np.stack([x_grid, y_grid], axis=-1)

print(f"Point grid shape: {point_grid.shape}")  # [column_idx, row_idx, sample_x, sample_y]

# ----------------------------------------------------------------
# 加载 SAM2 模型
# ----------------------------------------------------------------
predictor = SAM2ImagePredictor.from_pretrained("facebook/sam2-hiera-large")

# 确保在GPU上执行
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
predictor.model.to(device)

# ----------------------------------------------------------------
# inference
# ----------------------------------------------------------------
masks = []
with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
    predictor.set_image(image)
with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
    for j in range(point_grid.shape[1]):
        for i in range(point_grid.shape[0]):
            point_coord = np.expand_dims(point_grid[i, j], axis=0)
            point_label = np.array([1])
            current_masks, _, _ = predictor.predict(point_coords=point_coord, point_labels=point_label)
            masks.append(current_masks[0].astype(bool))

# ----------------------------------------------------------------
# filter
# ----------------------------------------------------------------
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

        # # get neighboring masks
        # neighbors = []
        # if i != 0:
        #     neighbors.append(masks[i - 1, j])
        # if j != 0:
        #     neighbors.append(masks[i, j - 1])

        
        # check for overlap
        # overlap = False
        # if neighbors:
        #     for neighbor in neighbors:
        #         if is_overlap(neighbor, masks[i, j], FILTER_OVERLAP_RATIO):
        #             overlap = True    
        #             break
        
        if is_overlap(segment_mask, masks[i, j], FILTER_OVERLAP_RATIO):
            print(i, j)
            segment_mask = segment_mask.astype(bool) | masks[i, j].astype(bool)
            continue

        filtered_masks.append(masks[i, j])
        legal_sample_points.append(point_grid[j, i])
        segment_mask = segment_mask.astype(bool) | masks[i, j].astype(bool)
                
masks = filtered_masks


# ----------------------------------------------------------------
# visualization 
# ----------------------------------------------------------------
# 将所有mask合并成一个彩色图像
combined_mask = np.zeros((height, width, 3), dtype=np.uint8)

# 为每个mask分配不同的颜色
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

for i, mask in enumerate(masks):
    color = colors[i % len(colors)]
    # 将当前mask区域设置为对应颜色
    combined_mask[mask > 0] = color

# 将原图和mask叠加显示
alpha = 0.5
overlay = image.copy()
overlay = cv2.addWeighted(image, 1-alpha, combined_mask, alpha, 0)

# 在图上标记采样点
for point in legal_sample_points:
    x, y = int(point[0]), int(point[1])
    cv2.circle(overlay, (x, y), radius=5, color=(255, 255, 255), thickness=-1)

# 保存结果到seg.jpg
cv2.imwrite("seg.jpg", cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))