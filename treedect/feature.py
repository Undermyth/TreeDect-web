import torch
import numpy as np
from torch.utils.data import Dataset
import cv2

class FeatureExtractionDataset(Dataset):
    def __init__(self, palette: np.ndarray, image, n_patch, segment_ratio = 4):
        super().__init__()
        self.palette = palette
        self.segment_ratio = segment_ratio
        self.height = self.palette.shape[0]
        self.width = self.palette.shape[1]
        self.n_patch = n_patch
        self.image = image

        self.num_segs = int(palette.max())
        
        self.left = [float('inf') for _ in range(self.num_segs)]
        self.top = [float('inf') for _ in range(self.num_segs)]   # left up corner
        self.right = [0 for _ in range(self.num_segs)]
        self.bottom = [0 for _ in range(self.num_segs)]    # right down corner

        self._generate_dataset()
        self._generate_selection()

        self._visualization()

    def _generate_dataset(self):

        for i in range(self.height):
            for j in range(self.width):
                index = int(self.palette[i, j]) - 1
                if index != -1: # 0 (no segment), but -1
                    self.left[index] = min(self.left[index], j)
                    self.top[index] = min(self.top[index], i)
                    self.right[index] = max(self.right[index], j)
                    self.bottom[index] = max(self.bottom[index], i)

        self.left = np.array(self.left).astype(np.int32)
        self.top = np.array(self.top).astype(np.int32)
        self.right = np.array(self.right).astype(np.int32)
        self.bottom = np.array(self.bottom).astype(np.int32)

        center_h = (self.top + self.bottom) / 2
        center_w = (self.left + self.right) / 2

        seg_width = self.width / self.segment_ratio
        seg_height = self.height / self.segment_ratio

        bbox_left = np.round(center_w) - seg_width / 2
        bbox_top = np.round(center_h) - seg_height / 2
        bbox_right = np.round(center_w) + seg_width / 2
        bbox_bottom = np.round(center_h) + seg_height / 2

        # print(center_h, center_w)
        # print(bbox_left, bbox_top, bbox_right, bbox_bottom)

        mask = bbox_left < 0
        bbox_right = bbox_right + mask * (0 - bbox_left)
        bbox_left = bbox_left + mask * (0 - bbox_left)

        mask = bbox_top < 0
        bbox_bottom = bbox_bottom + mask * (0 - bbox_top)
        bbox_top = bbox_top + mask * (0 - bbox_top)

        mask = bbox_right > self.width
        bbox_left = bbox_left - mask * (bbox_right - self.width)
        bbox_right = bbox_right - mask * (bbox_right - self.width)

        mask = bbox_bottom > self.height
        bbox_top = bbox_top - mask * (bbox_bottom - self.height)
        bbox_bottom = bbox_bottom - mask * (bbox_bottom - self.height)

        self.bbox_left = bbox_left
        self.bbox_right = bbox_right
        self.bbox_top = bbox_top
        self.bbox_bottom = bbox_bottom

    def _visualization(self):
        vis_image = self.image.copy()
        colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
        for i in range(5):
            x1 = int(self.bbox_left[i])
            y1 = int(self.bbox_top[i])
            x2 = int(self.bbox_right[i])
            y2 = int(self.bbox_bottom[i])
            color = colors[i % len(colors)]
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
        cv2.imwrite('visualization.png', vis_image)

    def _generate_selection(self):

        width = self.bbox_right - self.bbox_left
        height = self.bbox_bottom - self.bbox_top
        patch_width = width / self.n_patch
        patch_height = height / self.n_patch

        self.mask_start_width = np.floor((self.left - self.bbox_left) / patch_width)
        self.mask_start_height = np.floor((self.top - self.bbox_top) / patch_height)
        self.mask_end_width = np.ceil((self.right - self.bbox_left) / patch_width)
        self.mask_end_height = np.ceil((self.bottom - self.bbox_top) / patch_height)

    def __getitem__(self, index):
        return {
            "data": self.image[int(self.bbox_top[index]):int(self.bbox_bottom[index]), int(self.bbox_left[index]):int(self.bbox_right[index]), :],
            "mask": np.array([self.mask_start_height[index], self.mask_start_width[index], self.mask_end_height[index], self.mask_end_width[index]])
        }

    def __len__(self):
        return self.num_segs

    @staticmethod
    def collate_fn(batch):
        return {
            "data": [sample["data"] for sample in batch],
            "mask": np.stack([sample["mask"] for sample in batch], axis=0)
        }



if __name__ == '__main__':
    circle = np.array([
        [0, 0, 1, 1, 1, 0],
        [0, 0, 1, 1, 2, 3],
        [0, 1, 1, 2, 2, 2],
        [0, 0, 1, 1, 2, 2],
        [4, 4, 4, 0, 0, 2],
        [4, 0, 4, 0, 0, 0]
    ])
    img = np.zeros((12, 12))
    img[6:6+circle.shape[0], 6:6+circle.shape[1]] += circle
    print(img)
    dataset = FeatureExtractionDataset(img, None, 2)
    print(dataset.left, dataset.top, dataset.right, dataset.bottom)