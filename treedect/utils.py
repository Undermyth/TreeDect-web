import numpy as np
from sam2.sam2_image_predictor import SAM2ImagePredictor
from typing import List, Tuple
import numba

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
                # print(i, j)
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
    # synthetic sanity check passed
    valid_blocks = set()
    patch_width = (bbox_right - bbox_left + 1) / n_patch
    patch_height = (bbox_bottom - bbox_top + 1) / n_patch
    for x in range(bbox_top, bbox_bottom + 1):
        for y in range(bbox_left, bbox_right + 1):
            if palette[x, y] == index:
                block_x = (x - bbox_top) // patch_height
                block_y = (y - bbox_left) // patch_width
                valid_blocks.add(int(block_x * n_patch + block_y))
    return sorted(list(valid_blocks))

@numba.jit(nopython=True)
def create_block_mask_in_global(bbox_top, bbox_bottom, bbox_left, bbox_right, palette, index, n_patch):
    '''
    the whole palette is divided into n_patch x n_patch blocks.
    this function found the patch that really contains the segment, and return in raster scan order.
    actually bbox_* is not computationally necessary, but it has already been computed in the previous step.
    '''
    patch_height = palette.shape[1] // n_patch
    patch_width = palette.shape[0] // n_patch
    patch_idx_start = bbox_top // patch_height
    patch_idx_end = bbox_bottom // patch_height
    patch_idy_start = bbox_left // patch_width
    patch_idy_end = bbox_right // patch_width
    
    # fast checking. many cases should fall into this condition, which does not need extra computation
    if patch_idx_start == patch_idx_end and patch_idy_start == patch_idy_end:
        return 1

    block_count = 0

    for patch_idx in range(patch_idx_start, patch_idx_end + 1):
        for patch_idy in range(patch_idy_start, patch_idy_end + 1):
            # scan the bounding box for evidence
            done = False
            for x in range(bbox_top, bbox_bottom + 1):
                for y in range(bbox_left, bbox_right + 1):
                    if palette[x, y] == index:
                        block_x = x // patch_height
                        block_y = y // patch_width
                        if block_x == patch_idx and block_y == patch_idy:
                            block_count += 1
                            done = True
                            break
                if done:
                    break
    
    return block_count

if __name__ == '__main__':
    palette = np.array([
        [0, 0, 1, 1, 1, 0],
        [0, 0, 1, 1, 2, 3],
        [0, 1, 2, 2, 2, 2],
        [0, 0, 1, 3, 2, 2],
        [4, 4, 4, 0, 0, 2],
        [4, 0, 4, 0, 0, 0]
    ])

    # bbox_left = 2
    # bbox_right = 5
    # bbox_top = 1
    # bbox_bottom = 4
    # n_patch = 2
    # index = 2

    bbox_left = 1
    bbox_right = 4
    bbox_top = 0
    bbox_bottom = 3
    n_patch = 3
    index = 1

    # print(create_block_mask_in_bbox(bbox_top, bbox_bottom, bbox_left, bbox_right, palette, index, n_patch))
    print(create_block_mask_in_global(bbox_top, bbox_bottom, bbox_left, bbox_right, palette, index, n_patch))
