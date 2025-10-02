<template>
  <div class="settings-container">
    <n-space vertical>
      <n-input-number v-model:value="horizontalSampling" placeholder="横向采样频率" />
      <n-input-number v-model:value="verticalSampling" placeholder="纵向采样频率" />
      <n-input-number v-model:value="overlapThreshold" placeholder="重合比阈值" />
      <n-button type="primary" @click="generateSegmentation">生成分割</n-button>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NInputNumber, NSpace, NButton } from 'naive-ui'

const horizontalSampling = ref<number>(50)
const verticalSampling = ref<number>(50)
const overlapThreshold = ref<number>(0.2)

const generateSegmentation = () => {
  // 这里可以添加生成分割的逻辑
  console.log('生成分割', {
    horizontalSampling: horizontalSampling.value,
    verticalSampling: verticalSampling.value,
    overlapThreshold: overlapThreshold.value
  })
}
</script>

<style scoped>
.settings-container {
  padding: 20px;
}
</style>