<template>
  <div class="settings-container">
    <n-space vertical>
      <n-input-number v-model:value="horizontalSampling" placeholder="横向采样频率" />
      <n-input-number v-model:value="verticalSampling" placeholder="纵向采样频率" />
      <n-input-number v-model:value="overlapThreshold" placeholder="重合比阈值" />
      <n-button type="primary" @click="generateSegmentation" :loading="loading">生成分割</n-button>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios';
import { NButton, NInputNumber, NSpace } from 'naive-ui';
import pako from 'pako';
import { ref } from 'vue';

const horizontalSampling = ref<number>(50)
const verticalSampling = ref<number>(50)
const overlapThreshold = ref<number>(0.2)
const loading = ref<boolean>(false)

// 定义解压mask数据的函数
function decompressMask(encodedMask: string, shape: [number, number]): boolean[] {
  // base64解码
  const compressedBytes = Uint8Array.from(atob(encodedMask), c => c.charCodeAt(0));
  // gzip解压
  const decompressedBytes = pako.inflate(compressedBytes);
  // 解包bits
  const unpacked = new Uint8Array(decompressedBytes.length * 8);
  for (let i = 0; i < decompressedBytes.length; i++) {
    for (let j = 0; j < 8; j++) {
      unpacked[i * 8 + j] = (decompressedBytes[i] >> (7 - j)) & 1;
    }
  }
  // 调整大小到原始图像尺寸
  return Array.from(unpacked.slice(0, shape[0] * shape[1])).map(val => val === 1);
}

const generateSegmentation = async () => {
  loading.value = true;
  try {
    const response = await axios.post('/generate_segmentation', {
      row_sample_interval: horizontalSampling.value,
      col_sample_interval: verticalSampling.value,
      overlap_ratio: overlapThreshold.value
    });
    
    const data = response.data;
    
    // 处理返回的数据
    console.log('生成分割结果:', {
      horizontalSampling: horizontalSampling.value,
      verticalSampling: verticalSampling.value,
      overlapThreshold: overlapThreshold.value
    });
    
    // 解析mask数据
    const { masks, sample_points, image_shape } = data;
    const decompressedMasks = masks.map((mask: string) => 
      decompressMask(mask, [image_shape[0], image_shape[1]])
    );
    
    // 输出处理结果
    console.log('解压后的mask数量:', decompressedMasks.length);
    console.log('采样点数量:', sample_points.length);
    console.log('图像尺寸:', image_shape);
    
    // 这里可以将数据传递给其他组件或进行可视化处理
    // 例如: emit到父组件或存储到全局状态管理中
    
  } catch (error) {
    console.error('生成分割时出错:', error);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.settings-container {
  padding: 20px;
}
</style>