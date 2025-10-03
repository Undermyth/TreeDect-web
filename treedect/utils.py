import numpy as np
from sam2.sam2_image_predictor import SAM2ImagePredictor

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
