<template>
  <div class="canvas-container">
    <div class="stage-wrapper">
      <v-stage ref="stage" :config="stageConfig" @wheel="handleWheel">
        <v-layer ref="layer">
          <v-image :config="imageConfig" v-if="imageConfig.image" @dragstart="handleDragStart" @dragend="handleDragEnd"/>
        </v-layer>
      </v-stage>
    </div>
    <div class="button-wrapper">
      <n-button type="primary" @click="loadImage">加载图像</n-button>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios';
import { NButton } from 'naive-ui';
import { onMounted, onUnmounted, ref } from 'vue';

const stageConfig = ref({
    width: 0,
    height: 0,
});

// 如果需要访问stage和layer的引用
const stage = ref(null);
const layer = ref(null);

// 新增图像配置
const imageConfig = ref({
  image: null,
  x: 0,
  y: 0,
  width: 0,
  height: 0,
  draggable: true
});

// 处理拖拽开始
function handleDragStart() {
  console.log('开始拖拽');
}

// 处理拖拽结束
function handleDragEnd() {
  console.log('结束拖拽');
}

// 处理鼠标滚轮缩放
function handleWheel(e) {
  e.evt.preventDefault();
  if (!imageConfig.value.image) return;
  
  const stage = stage.value.getNode();
  const pointer = stage.getPointerPosition();
  
  const oldScale = imageConfig.value.width / imageConfig.value.image.width;
  const scaleBy = 1.05; // 缩放因子
  const newScale = e.evt.deltaY > 0 ? oldScale * scaleBy : oldScale / scaleBy;
  
  // 限制缩放范围
  if (newScale < 0.1 || newScale > 10) return;
  
  // 计算新的图像尺寸
  const newWidth = imageConfig.value.image.width * newScale;
  const newHeight = imageConfig.value.image.height * newScale;
  
  // 计算缩放中心点相对于图像的位置
  const mousePointTo = {
    x: (pointer.x - imageConfig.value.x) / oldScale,
    y: (pointer.y - imageConfig.value.y) / oldScale,
  };
  
  // 更新图像位置和尺寸
  imageConfig.value.x = pointer.x - mousePointTo.x * newScale;
  imageConfig.value.y = pointer.y - mousePointTo.y * newScale;
  imageConfig.value.width = newWidth;
  imageConfig.value.height = newHeight;
}

// 加载图像函数
async function loadImage() {
    try {
        const response = await axios.post('/load_image');
        const data = response.data;
        const base64Image = data.image; // 假设返回的base64图像在image字段中
        
        // 创建Image对象
        const img = new Image();
        img.src = `data:image/png;base64,${base64Image}`;
        
        // 图像加载完成后更新imageConfig
        img.onload = () => {
            // 获取stage容器的实际尺寸
            const stageWidth = stageConfig.value.width;
            const stageHeight = stageConfig.value.height;
            
            // 计算图像缩放比例以适应stage
            const scale = Math.min(stageWidth / img.width, stageHeight / img.height);
            const scaledWidth = img.width * scale;
            const scaledHeight = img.height * scale;
            
            imageConfig.value.image = img;
            imageConfig.value.x = (stageWidth - scaledWidth) / 2;
            imageConfig.value.y = (stageHeight - scaledHeight) / 2;
            imageConfig.value.width = scaledWidth;
            imageConfig.value.height = scaledHeight;
        };
    } catch (error) {
        console.error('加载图像失败:', error);
    }
    console.log('image load complete');
}

// 更新stage尺寸
function updateStageSize() {
  const wrapper = document.querySelector('.stage-wrapper');
  if (wrapper) {
    stageConfig.value.width = wrapper.clientWidth;
    stageConfig.value.height = wrapper.clientHeight;
  }
}

// 监听窗口大小变化
function handleResize() {
  updateStageSize();
  // 如果已加载图像，重新调整图像大小
  if (imageConfig.value.image) {
    loadImage();
  }
}

onMounted(() => {
  updateStageSize();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.canvas-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px 5%; /* 左右各5%的padding */
  width: 90%;
  box-sizing: border-box;
}

.stage-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f5f5;
}

.button-wrapper {
  height: 5%;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 90%; /* 与绘图区保持一致 */
  margin: 0 auto;
}
</style>