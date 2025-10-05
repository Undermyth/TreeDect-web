<template>
  <div class="settings-container">
    <n-space vertical>
      <n-input-number v-model:value="horizontalSampling" placeholder="横向采样频率" />
      <n-input-number v-model:value="verticalSampling" placeholder="纵向采样频率" />
      <n-input-number v-model:value="overlapThreshold" placeholder="重合比阈值" />
      <n-button type="primary" @click="generateSegmentation" :loading="loading">生成分割</n-button>
      <n-switch v-model:value="segStore.showMask" />
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { useSegStore } from '@/stores/SegStore';
import axios from 'axios';
import { NButton, NInputNumber, NSpace, NSwitch } from 'naive-ui';
import pako from 'pako';
import { ref } from 'vue';

const horizontalSampling = ref<number>(50)
const verticalSampling = ref<number>(50)
const overlapThreshold = ref<number>(0.5)
const loading = ref<boolean>(false)
const segStore = useSegStore();

const generateSegmentation = async () => {
  loading.value = true;
  try {
    const response = await axios.post('/generate_segmentation', {
      row_sample_interval: horizontalSampling.value,
      col_sample_interval: verticalSampling.value,
      overlap_ratio: overlapThreshold.value
    });
    
    const data = response.data;
    
    // 解码base64编码的palette数据并转换为int32格式
    const paletteBuffer = Uint8Array.from(atob(data.palette), c => c.charCodeAt(0));
    const inflatedBuffer = pako.inflate(paletteBuffer);
    const paletteArray = new Int32Array(inflatedBuffer.buffer, inflatedBuffer.byteOffset, inflatedBuffer.byteLength / 4);
    
    // 将一维数组重构为二维数组
    const height = data.height;
    const width = data.width;
    const palette2D = new Array(height);
    for (let i = 0; i < height; i++) {
      palette2D[i] = new Array(width);
      for (let j = 0; j < width; j++) {
        palette2D[i][j] = paletteArray[i * width + j];
      }
    }
    
    // 保存到全局store
    segStore.setPalette(palette2D);
    console.log('mask数量:', data.num_masks);
    console.log('size', height, width);
    
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