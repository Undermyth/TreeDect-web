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
import { useSegStore } from '@/stores/SegStore';
import axios from 'axios';
import { NButton } from 'naive-ui';
import { onMounted, onUnmounted, ref, watch } from 'vue';

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

const segStore = useSegStore();

// 监视palette变化
watch(
  () => segStore.palette,
  (newPalette) => {
    // 检查palette是否为空
    if (newPalette && newPalette.length > 0) {
      console.log('Palette updated:', newPalette);
    }
  },
  { deep: true }
);

// 处理拖拽开始
const handleDragStart = () => {
  console.log('开始拖拽');
};

// 处理拖拽结束
const handleDragEnd = () => {
  console.log('结束拖拽');
};

const handleWheel = (e) => {
  e.evt.preventDefault();

  // 修复：使用正确的stage引用
  const stageNode = stage.value.getNode();
  const oldScale = stageNode.scaleX();
  const pointer = stageNode.getPointerPosition();

  const mousePointTo = {
    x: (pointer.x - stageNode.x()) / oldScale,
    y: (pointer.y - stageNode.y()) / oldScale,
  };

  // how to scale? Zoom in? Or zoom out?
  let direction = e.evt.deltaY < 0 ? 1 : -1;

  // when we zoom on trackpad, e.evt.ctrlKey is true
  // in that case lets revert direction
  if (e.evt.ctrlKey) {
    direction = -direction;
  }

  const scaleBy = 1.1;
  const newScale = direction > 0 ? oldScale * scaleBy : oldScale / scaleBy;

  stageNode.scale({ x: newScale, y: newScale });

  const newPos = {
    x: pointer.x - mousePointTo.x * newScale,
    y: pointer.y - mousePointTo.y * newScale,
  };
  stageNode.position(newPos);
};

// 加载图像函数
const loadImage = async () => {
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
};

// 更新stage尺寸
const updateStageSize = () => {
  const wrapper = document.querySelector('.stage-wrapper');
  if (wrapper) {
    stageConfig.value.width = wrapper.clientWidth;
    stageConfig.value.height = wrapper.clientHeight;
  }
};

// 监听窗口大小变化
const handleResize = () => {
  updateStageSize();
  // 如果已加载图像，重新调整图像大小
  if (imageConfig.value.image) {
    loadImage();
  }
};

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