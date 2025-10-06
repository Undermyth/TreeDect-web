from transformers import pipeline
from transformers.image_utils import load_image
from transformers import AutoImageProcessor, AutoModel
import torch
import time


url = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/pipeline-cat-chonk.jpeg"
image = load_image(url)

# 正确加载 processor（会读取官方配置）
processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
model = AutoModel.from_pretrained("facebook/dinov2-small")

# 检查 processor 的尺寸
print("Processor size:", processor.size)  # 应该是 {'height': 518, 'width': 518}
print(model.config.patch_size)
# 循环十次并计时，包括预处理过程
for i in range(10):
    start_time = time.time()
    
    # 预处理图像（包含在计时内）
    inputs = processor(
        images=image,
        return_tensors="pt",
        size={"height": 224, "width": 224},   # 直接 resize 到 518x518
        crop_size=None,                       # 禁用 center crop
        do_center_crop=False
    )

    # inputs = processor(images=image, return_tensors='pt')
    
    # 模型推理
    with torch.no_grad():
        outputs = model(**inputs)
    
    end_time = time.time()
    print(f"Iteration {i+1}: {end_time - start_time:.4f} seconds")

print("Input shape:", inputs.pixel_values.shape)  # [1, 3, 518, 518]
print("Token count:", outputs.last_hidden_state.shape[1])  # 1370