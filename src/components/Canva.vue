<template>
  <div class="canvas-container">
    <div class="stage-wrapper">
      <v-stage ref="stage" :config="stageConfig" @wheel="handleWheel" @click="handleClick" @contextmenu="handleRightClick">
        <v-layer ref="layer">
          <v-image :config="imageConfig" v-if="imageConfig.image" @dragstart="handleDragStart" @dragend="handleDragEnd"/>
          <!-- 添加用于显示分割结果的图层 -->
          <v-image :config="segmentationOverlayConfig" v-if="segmentationOverlayConfig.image && segStore.showMask"/>
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
import pako from 'pako';
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { PaletteImage } from './Canva';

// 如果需要访问stage和layer的引用
const stage = ref(null);
const layer = ref(null);
const paletteImage = ref(null);
const segStore = useSegStore();

// 添加鼠标位置响应式变量
const mousePosition = ref({ x: 0, y: 0 });

const stageConfig = ref({
    width: 0,
    height: 0,
    draggable: true,
});

// 新增图像配置
const imageConfig = ref({
  image: null,
  x: 0,
  y: 0,
  width: 0,
  height: 0,
  draggable: false
});

// 分割图层配置
const segmentationOverlayConfig = ref({
  image: null,
  x: 0,
  y: 0,
  width: 0,
  height: 0,
  draggable: false,
  opacity: 0.6
});

// ---------------------------------------------------------------
// util functions
// ---------------------------------------------------------------
const imgScaleFit = (img, imgConfig) => {
  // 获取stage容器的实际尺寸
  const stageWidth = stageConfig.value.width;
  const stageHeight = stageConfig.value.height;
  
  // 修复：使用正确的图像变量segImg而不是img
  const scale = Math.min(stageWidth / img.width, stageHeight / img.height);
  const scaledWidth = img.width * scale;
  const scaledHeight = img.height * scale;
  
  imgConfig.value.image = img;
  imgConfig.value.x = (stageWidth - scaledWidth) / 2;
  imgConfig.value.y = (stageHeight - scaledHeight) / 2;
  imgConfig.value.width = scaledWidth;
  imgConfig.value.height = scaledHeight;
}

// 监视palette变化
watch(
  () => segStore.palette,
  async (newPalette) => {
    // 检查palette是否为空
    if (newPalette && newPalette.length > 0) {
      // 生成分割图像并显示
      console.log('start visualizing mask');
      paletteImage.value = new PaletteImage(newPalette);
      const segImg = new Image();
      segImg.src = await paletteImage.value.getBase64();
      segImg.onload = () => {
        imgScaleFit(segImg, segmentationOverlayConfig);
        // 强制Konva重新绘制图层
        if (layer.value) {
          layer.value.getNode().batchDraw();
        }
      };
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

// 处理鼠标移动事件
const handleClick = async (e) => {
  // 获取stage节点
  const stageNode = stage.value.getNode();
  
  // 获取鼠标在stage中的位置
  const pointer = stageNode.getPointerPosition();
  
  // 获取当前图像的配置信息
  const imgConfig = imageConfig.value;
  
  if (imgConfig.image) {
    // 获取stage的当前位置（拖动后的偏移）和缩放因子
    const stagePosition = stageNode.position();
    const stageScale = stageNode.scale();
    
    // 计算鼠标在图像上的相对位置（考虑stage的偏移和缩放）
    const relativeX = (pointer.x - stagePosition.x - imgConfig.x) / stageScale.x;
    const relativeY = (pointer.y - stagePosition.y - imgConfig.y) / stageScale.y;
    
    // 考虑图像缩放比例，计算实际像素位置
    const scaleX = imgConfig.width / imgConfig.image.width;
    const scaleY = imgConfig.height / imgConfig.image.height;
    
    // 计算图像上的实际像素坐标
    const pixelX = Math.floor(relativeX / scaleX);
    const pixelY = Math.floor(relativeY / scaleY);
    
    // 更新鼠标位置
    mousePosition.value = { x: pixelX, y: pixelY };
    console.log(pointer.x, pointer.y, imgConfig.x, imgConfig.y);
    
    // 打印鼠标在图像上的像素位置
    if (paletteImage.value) {
      await paletteImage.value.delete(pixelX, pixelY);
      const segImg = new Image();
      segImg.src = await paletteImage.value.getBase64();
      segImg.onload = () => {
        imgScaleFit(segImg, segmentationOverlayConfig);
        // 强制Konva重新绘制图层
        if (layer.value) {
          layer.value.getNode().batchDraw();
        }
      };
    }
  }
};

const handleRightClick = async (e) => {
  // 阻止默认的右键菜单行为
  e.evt.preventDefault();
  
  // 获取stage节点
  const stageNode = stage.value.getNode();
  
  // 获取鼠标在stage中的位置
  const pointer = stageNode.getPointerPosition();
  
  // 获取当前图像的配置信息
  const imgConfig = imageConfig.value;
  
  if (imgConfig.image) {
    // 获取stage的当前位置（拖动后的偏移）和缩放因子
    const stagePosition = stageNode.position();
    const stageScale = stageNode.scale();
    
    // 计算鼠标在图像上的相对位置（考虑stage的偏移和缩放）
    const relativeX = (pointer.x - stagePosition.x - imgConfig.x) / stageScale.x;
    const relativeY = (pointer.y - stagePosition.y - imgConfig.y) / stageScale.y;
    
    // 考虑图像缩放比例，计算实际像素位置
    const scaleX = imgConfig.width / imgConfig.image.width;
    const scaleY = imgConfig.height / imgConfig.image.height;
    
    // 计算图像上的实际像素坐标
    const pixelX = Math.floor(relativeX / scaleX);
    const pixelY = Math.floor(relativeY / scaleY);
    
    // 更新鼠标位置
    mousePosition.value = { x: pixelX, y: pixelY };

    try {
      const response = await axios.post('/point_segment', {
        x: pixelX,
        y: pixelY,
      })
      const data = response.data;
      // 解码base64编码的palette数据并转换为int32格式
      const maskBuffer = Uint8Array.from(atob(data.mask), c => c.charCodeAt(0));
      const inflatedBuffer = pako.inflate(maskBuffer);
      const maskArray = new Int32Array(inflatedBuffer.buffer, inflatedBuffer.byteOffset, inflatedBuffer.byteLength / 4);
      
      // 将一维数组重构为二维数组
      const height = data.height;
      const width = data.width;
      const mask2D = new Array(height);
      for (let i = 0; i < height; i++) {
        mask2D[i] = new Array(width);
        for (let j = 0; j < width; j++) {
          mask2D[i][j] = maskArray[i * width + j];
        }
      }
      await paletteImage.value.update(mask2D);
    } catch (error) {
      console.error('点预测时出现错误:', error);
    }
    
    // 移除了重复的delete调用，避免覆盖刚更新的结果
    // 这里不再调用delete，因为我们只想更新而不删除
    if (paletteImage.value) {
      const segImg = new Image();
      segImg.src = await paletteImage.value.getBase64();
      segImg.onload = () => {
        imgScaleFit(segImg, segmentationOverlayConfig);
        // 强制Konva重新绘制图层
        if (layer.value) {
          layer.value.getNode().batchDraw();
        }
      };
    }
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