# %%
import torch
import numpy as np
from torch.utils.data import Dataset
import cv2

from utils import create_block_mask_in_bbox

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

        self.area = [0 for _ in range(self.num_segs)]

        self.valid = [1 for _ in range(self.num_segs)]

        self._generate_dataset()

        self._visualization()

        # import pickle
        # pickle.dump(self.palette, open("palette.pkl", "wb"))
        # pickle.dump(self.image, open("image.pkl", "wb"))

    def _generate_dataset(self):

        for i in range(self.height):
            for j in range(self.width):
                index = int(self.palette[i, j]) - 1
                if index != -1: # 0 (no segment), but -1
                    self.left[index] = min(self.left[index], j)
                    self.top[index] = min(self.top[index], i)
                    self.right[index] = max(self.right[index], j)
                    self.bottom[index] = max(self.bottom[index], i)
                    self.area[index] += 1

        for i in range(self.num_segs):
            if self.left[i] == float('inf'):
                self.left[i] = 0
                self.top[i] = 0
                self.right[i] = 10
                self.bottom[i] = 10
                self.valid[i] = 0

        self.left = np.array(self.left).astype(np.int32)
        self.top = np.array(self.top).astype(np.int32)
        self.right = np.array(self.right).astype(np.int32)
        self.bottom = np.array(self.bottom).astype(np.int32)

        self.bbox_left = self.left
        self.bbox_top = self.top
        self.bbox_right = self.right
        self.bbox_bottom = self.bottom

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

    def __getitem__(self, index):
        bbox = self.image[int(self.bbox_top[index]):int(self.bbox_bottom[index]) + 1, int(self.bbox_left[index]):int(self.bbox_right[index]) + 1, :]
        cutted_palette = self.palette[int(self.bbox_top[index]):int(self.bbox_bottom[index]) + 1, int(self.bbox_left[index]):int(self.bbox_right[index]) + 1]
        mask = (cutted_palette != index + 1).astype(np.bool)
        bbox[mask] = np.array([0, 0, 0], dtype=np.uint8)
        block_mask = create_block_mask_in_bbox(self.bbox_top[index], self.bbox_bottom[index], self.bbox_left[index], self.bbox_right[index], self.palette, index + 1, self.n_patch)
        return {
            "data": bbox,
            "block_mask": np.array(block_mask, dtype=np.int32)
        }

    def __len__(self):
        return self.num_segs

    @staticmethod
    def collate_fn(batch):
        return {
            "data": [sample["data"] for sample in batch],
            "block_mask": [sample["block_mask"] for sample in batch]
        }

# %%
if __name__ == '__main__':
    import pickle
    import cv2
    import matplotlib.pyplot as plt
    # np.set_printoptions(threshold=10000)
    image = pickle.load(open("image.pkl", "rb"))
    palette = pickle.load(open("palette.pkl", "rb"))
    dataset = FeatureExtractionDataset(palette, image, 2)
    img = dataset[70]['data']
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.show()
# %%
