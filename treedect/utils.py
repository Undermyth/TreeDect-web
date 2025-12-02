import numpy as np
from sam2.sam2_image_predictor import SAM2ImagePredictor
from typing import List, Tuple

def generation_sample_grid(height: int, width: int, ROW_SAMPLE_INTERVAL: int, COL_SAMPLE_INTERVAL: int):
    """
    生成一个二维网格点阵，用于在图像上进行采样。

    该函数根据给定的行和列采样间隔，在指定的图像尺寸内生成均匀分布的采样点。
    采样点会根据计算出的padding进行居中调整，确保不会超出图像边界。

    Args:
        height (int): 图像高度
        width (int): 图像宽度
        ROW_SAMPLE_INTERVAL (int): 行采样间隔（垂直方向）
        COL_SAMPLE_INTERVAL (int): 列采样间隔（水平方向）

    Returns:
        numpy.ndarray: 形状为 (column_idx, row_idx, 2) 的三维数组，
                      其中最后一个维度包含采样点的 [x, y] 坐标

    Note:
        - 坐标系统以图像左上角为原点 (0, 0)
        - x坐标对应列索引，y坐标对应行索引
        - 采样点会自动进行居中padding调整
    """
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
    point_grid = np.stack([x_grid, y_grid], axis=-1)    # [column_idx, row_idx, sample_x, sample_y]
    return point_grid

def filter_overlap_segments(
    point_grid: List[np.ndarray], 
    masks: List[np.ndarray], 
    height: int,
    width: int,
    ratio: float
) -> Tuple[List[np.ndarray], List[np.ndarray]]:

    filtered_masks = []
    legal_sample_points = []
    masks = np.stack(masks, axis=0)
    masks = masks.reshape(point_grid.shape[1], point_grid.shape[0], height, width)
    segment_mask = np.zeros((height, width))

    def is_overlap(mask_a: np.ndarray, mask_b: np.ndarray, overlap_ratio: float) -> bool:
        overlap_mask = mask_a.astype(bool) & mask_b.astype(bool)
        ratio = overlap_mask.sum() / mask_b.sum()
        return ratio >= overlap_ratio

    for i in range(masks.shape[0]):
        for j in range(masks.shape[1]):

            if is_overlap(segment_mask, masks[i, j], ratio):
                print(i, j)
                segment_mask = segment_mask.astype(bool) | masks[i, j].astype(bool)
                continue

            filtered_masks.append(masks[i, j])
            legal_sample_points.append(point_grid[j, i])  
            segment_mask = segment_mask.astype(bool) | masks[i, j].astype(bool)
    
    return legal_sample_points, filtered_masks

def masks_to_palette(masks: List[np.ndarray], height: int, width: int) -> np.ndarray:

    palette = np.zeros((height, width)).astype(np.int32)
    for i, mask in enumerate(masks, start=1):
        # 1. new mask will not overwrite existing masks
        # 2. new mask is presented by idx
        palette_mask = (palette == 0)
        palette = palette + i * (mask & palette_mask)
    
    return palette.astype(np.int32)

def create_block_mask_in_bbox(bbox_top, bbox_bottom, bbox_left, bbox_right, palette, index, n_patch):
    '''
    the bounding box of a segment (marked by index on palette) is divided into n_patch x n_patch blocks.
    this function found the patch that really contains the segment, and return in raster scan order.
    actually bbox_* is not computationally necessary, but it has already been computed in the previous step.
    '''
    valid_blocks = set()
    patch_width = (bbox_right - bbox_left) / n_patch
    patch_height = (bbox_bottom - bbox_top) / n_patch
    for x in range(bbox_left, bbox_right):
        for y in range(bbox_top, bbox_bottom):
            if palette[x, y] == index:
                block_x = (x - bbox_top) // patch_height
                block_y = (y - bbox_left) // patch_width
                valid_blocks.add(block_x * n_patch + block_y)
    return sorted(list(valid_blocks))
