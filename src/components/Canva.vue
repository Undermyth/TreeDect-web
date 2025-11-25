<template>
  <div class="canvas-container">
    <div class="stage-wrapper" @contextmenu="handleRightClick">
      <n-dropdown
        placement="bottom-start"
        trigger="manual"
        :x="menuX"
        :y="menuY"
        :options="menuOptions"
        :show="showDropdown"
        :on-clickoutside="onClickoutside"
        @select="handleSelect"
      />
      <v-stage 
        ref="stage"
        :config="stageConfig" 
        @mousedown="handleMouseDown"
        @mousemove="handleMove"
        @mouseup="handleMouseUp"
        @wheel="handleWheel"
        @touchstart="handleMouseDown"
        @touchmove="handleMove"
        @touchend="handleMouseUp"
      >
        <v-layer ref="layer">
          <v-image :config="imageConfig" v-if="imageConfig.image"/>
        </v-layer>
        <v-layer ref="segLayer">
          <v-image :config="segmentationOverlayConfig" v-if="segmentationOverlayConfig.image && segStore.showMask"/>
        </v-layer>
      </v-stage>
    </div>
    <div class="button-wrapper">
      <input 
        type="file" 
        ref="fileInput" 
        style="display: none;" 
        accept="image/*,.tiff,.tif" 
        @change="loadImage"
      />
      <n-button type="primary" @click="handleFileInputClick">加载图像</n-button>
      <n-button type="primary" @click="handleCluster" :loading="inCluster">无监督分类</n-button>
      <n-button type="primary" @click="finishEdit" :disabled="!editMode">完成编辑</n-button>
    </div>
  </div>
</template>

<script setup>
import { useSegStore } from '@/stores/SegStore';
import axios from 'axios';
import { NButton, NDropdown } from 'naive-ui';
import pako from 'pako';
import UTIF from 'utif2';
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { PaletteImage } from './Canva';

// 如果需要访问stage和layer的引用
const stage = ref(null);
const layer = ref(null);
const segLayer = ref(null);
const paletteImage = ref(null);
const segStore = useSegStore();
const drawIndex = ref(null);
const clusterIndexes = ref([]);

// 添加鼠标位置响应式变量
const mousePosition = ref({ x: 0, y: 0 });
const showDropdown = ref(false)
const menuX = ref(0)
const menuY = ref(0)
const editMode = ref(false);
const increment = ref(true);
const mouseDown = ref(false);
const inCluster = ref(false);

const stageConfig = ref({
    x: 0,
    y: 0,
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
  width: 0,
  height: 0,
  draggable: false,
  opacity: 1
});

const menuOptions = [
  {
    label: '删除',
    key: 'delete'
  },
  {
    label: '重新识别',
    key: 'segment'
  },
  {
    label: '调整（增加）',
    key: 'increment'
  },
  {
    label: '调整（删减）',
    key: 'decrement'
  }
]

// ---------------------------------------------------------------
// util functions
// ---------------------------------------------------------------

const setImgConfig = (canvas, imgConfig) => {
  const stageWidth = stageConfig.value.width;
  const stageHeight = stageConfig.value.height;
  
  // 修复：使用正确的图像变量segImg而不是img
  const scale = Math.min(stageWidth / canvas.width, stageHeight / canvas.height);
  const scaledWidth = canvas.width * scale;
  const scaledHeight = canvas.height * scale;
  
  imgConfig.value.image = canvas;
  imgConfig.value.x = (stageWidth - scaledWidth) / 2;
  imgConfig.value.y = (stageHeight - scaledHeight) / 2;
  imgConfig.value.width = scaledWidth;
  imgConfig.value.height = scaledHeight;
}

const getMousePixelPosition = () => {
  // 获取stage节点
  const stageNode = stage.value.getNode();
  
  // 获取鼠标在stage中的位置
  const pointer = stageNode.getPointerPosition();

  // 获取stage的当前位置（拖动后的偏移）和缩放因子
  const stagePosition = stageNode.position();
  const stageScale = stageNode.scale();
  // 计算鼠标在图像上的相对位置（考虑stage的偏移和缩放）
  const imgConfig = imageConfig.value;

  if (!imgConfig.image) {
    return null;
  }
  
  // 在缩放之后，屏幕上存在一个坐标系统；其中，stage 坐标系中的一个刻度对应于多个 pixel
  // pointer 和 stagePosition 是以 pixel 衡量的，imgConfig 始终是在 stage 坐标系下相对于 stage 原点衡量的
  const relativeX = (pointer.x - stagePosition.x) / stageScale.x - imgConfig.x;
  const relativeY = (pointer.y - stagePosition.y) / stageScale.y - imgConfig.y;
  
  // 考虑图像缩放比例，计算实际像素位置
  const scaleX = imgConfig.width / imgConfig.image.width;
  const scaleY = imgConfig.height / imgConfig.image.height;

  // 计算图像上的实际像素坐标
  const pixelX = Math.floor(relativeX / scaleX);
  const pixelY = Math.floor(relativeY / scaleY);
  return {x: pixelX, y: pixelY};
}

// ---------------------------------------------------------------
// monitor (rendering entry)
// 监视palette变化。这里是整个绘图的起点；Setting.vue 中将会向 pinia 写入新的 palette，然后在此处被监视，从而触发整个绘画
// NOTE：为了避免反复触发事件渲染花费大量时间，我们禁止从 Canva 组件一侧更改 pinia 中的全局 palette
// 该 palette 仅在初始化分割时进行传入，后续仅通过 mask 传播
// ---------------------------------------------------------------
watch(
  () => segStore.palette,
  async (newPalette) => {
    // 检查palette是否为空
    if (newPalette && newPalette.length > 0) {
      // 生成分割图像并显示
      console.time('palette rendering postprocessing');
      paletteImage.value = new PaletteImage(newPalette);
      const canvas = document.createElement('canvas');
      canvas.height = paletteImage.value.height;
      canvas.width = paletteImage.value.width;
      setImgConfig(canvas, segmentationOverlayConfig);
      const ctx = canvas.getContext('2d');
      paletteImage.value.fullRender(ctx, segLayer);
      console.timeEnd('palette rendering postprocessing');
    }
  },
  { deep: true }
);

watch(
  () => segStore.highlightCluster,
  (newHighlightCluster) => {
    const indexes = [];
    for (let i = 0; i < clusterIndexes.value.length; i++) {
      if (clusterIndexes.value[i] == newHighlightCluster) {
        indexes.push(i + 1);
      }
    }
    console.log(clusterIndexes.value, newHighlightCluster, indexes);
    const canvas = segmentationOverlayConfig.value.image;
    const ctx = canvas.getContext('2d');
    paletteImage.value.uniqueLight(ctx, segLayer, indexes);
  }
)

// ---------------------------------------------------------------
// mouse and wheel events
// ---------------------------------------------------------------
const handleMove = (e) => {
  if (!editMode.value || !mouseDown.value) {
    return;
  }
  const position = getMousePixelPosition();
  if (position) {
    const canvas = segmentationOverlayConfig.value.image;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      paletteImage.value.modify(ctx, segLayer, drawIndex.value, position.x, position.y, increment.value); 
    }
  }
}

const handleMouseDown = (e) => {
  mouseDown.value = true;
}

const handleMouseUp = (e) => {
  mouseDown.value = false;
}

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

// ---------------------------------------------------------------
// compositor actions
// ---------------------------------------------------------------

const handleFileInputClick = () => {
  // 触发隐藏的文件输入框点击事件
  const fileInput = document.querySelector('input[type="file"]');
  if (fileInput) {
    fileInput.click();
  }
};

// 加载图像函数
const loadImage = async (event) => {
  try {
    const file = event.target.files[0]; // 从事件中提取文件
    if (!file) {
      console.error('未选择文件');
      return;
    }

    // 检查是否为 TIFF 文件
    const isTiff = file.name.toLowerCase().endsWith('.tiff') || file.name.toLowerCase().endsWith('.tif');
    
    if (isTiff) {
      // 处理 TIFF 文件
      await loadTiffImage(file);
    } else {
      // 处理普通图像文件
      await loadRegularImage(file);
    }

  } catch (error) {
    console.error('加载或上传图像失败:', error);
  }
};

// 处理普通图像文件
const loadRegularImage = async (file) => {
  // 创建 FormData 对象并附加文件
  const formData = new FormData();
  formData.append('file', file); // 确保字段名与后端一致

  // 上传图像到后端接口
  const response = await axios.post('/load_image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data', // 设置请求头
    },
  });

  // 创建 FileReader 对象读取文件
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.src = e.target.result; // 将读取结果设置为图像源

    // 图像加载完成后更新 imageConfig
    img.onload = () => setImgConfig(img, imageConfig);
  };

  // 读取文件为 Data URL
  reader.readAsDataURL(file);
};

// 处理 TIFF 图像文件
const loadTiffImage = async (file) => {
  const arrayBuffer = await file.arrayBuffer();
  const ifds = UTIF.decode(arrayBuffer);
  const firstPage = ifds[0]; // 获取第一页
  UTIF.decodeImage(arrayBuffer, firstPage); // 解码图像
  
  const rgba = UTIF.toRGBA8(firstPage); // 转换为 RGBA
  const width = firstPage.width;
  const height = firstPage.height;
  
  // 创建 canvas 并绘制 TIFF 图像
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  
  // 创建 ImageData 对象
  const imageData = new ImageData(new Uint8ClampedArray(rgba), width, height);
  ctx.putImageData(imageData, 0, 0);
  
  // 将 canvas 转换为 Blob 并上传
  canvas.toBlob(async (blob) => {
    const jpegFile = new File([blob], 'converted.jpg', { type: 'image/jpeg' });
    
    // 创建 FormData 对象并附加转换后的文件
    const formData = new FormData();
    formData.append('file', jpegFile);
    
    // 上传图像到后端接口
    try {
      const response = await axios.post('/load_image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      // 显示转换后的图像
      const img = new Image();
      img.src = canvas.toDataURL('image/jpeg');
      img.onload = () => setImgConfig(img, imageConfig);
    } catch (error) {
      console.error('上传转换后的图像失败:', error);
    }
  }, 'image/jpeg', 0.9);
};

const finishEdit = () => {
  editMode.value = false;
  stageConfig.value.draggable = true;
}

// 更新stage尺寸
const updateStageSize = () => {
  const wrapper = document.querySelector('.stage-wrapper');
  if (wrapper) {
    stageConfig.value.width = wrapper.clientWidth;
    stageConfig.value.height = wrapper.clientHeight;
  }
};

const handleRightClick = async (e) => {
  // 阻止默认的右键菜单行为
  e.preventDefault();
  showDropdown.value = false;
  const position = getMousePixelPosition();
  if (position.x < 0 || position.x >= imageConfig.value.image.width || position.y < 0 || position.y >= imageConfig.value.image.height) {
    return;
  }
  mousePosition.value = { x: position.x, y: position.y };
  nextTick().then(() => {
    showDropdown.value = true;
    menuX.value = e.clientX;
    menuY.value = e.clientY;
  });
}

const onClickoutside = () => {
  showDropdown.value = false
}

const handleCluster = async () => {
  if (!paletteImage.value) {
    console.log('No palette image available for clustering');
    return;
  }

  inCluster.value = true;
  try {
    console.time('cluster request');
    const response = await axios.post('/cluster', {
      palette: paletteImage.value.palette,
      k: segStore.k
    });
    console.timeEnd('cluster request');
    const clusterMap = response.data.labels; // 修复：正确访问响应数据
    const canvas = segmentationOverlayConfig.value.image;
    const ctx = canvas.getContext('2d');
    paletteImage.value.cluster(ctx, segLayer, clusterMap);
    clusterIndexes.value = clusterMap;
    segStore.setColorMap(paletteImage.value.getHexColor());
    segStore.setAreas(response.data.areas);
  } catch (error) {
    console.error('聚类时出现错误:', error);
  } finally {
    inCluster.value = false;
  }
}

const handleSelect = async (key) => {

  if (key === 'delete') {
    if (paletteImage.value) {
      const canvas = segmentationOverlayConfig.value.image;
      const ctx = canvas.getContext('2d');
      paletteImage.value.delete(ctx, segLayer, mousePosition.value.x, mousePosition.value.y);
    }
  }

  else if (key === 'segment') {
    try {
      console.time('point_segment request');
      const response = await axios.post('/point_segment', {
        x: mousePosition.value.x,
        y: mousePosition.value.y,
      });
      console.timeEnd('point_segment request');
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
      const canvas = segmentationOverlayConfig.value.image;
      const ctx = canvas.getContext('2d');
      paletteImage.value.update(ctx, segLayer, mask2D);
    } catch (error) {
      console.error('点预测时出现错误:', error);
    }
  }

  else if (key === 'increment') {
    const index = paletteImage.value.getIndex(mousePosition.value.x, mousePosition.value.y);
    if (index == 0) {
      return;
    }
    editMode.value = true;
    increment.value = true;
    drawIndex.value = index;
    stageConfig.value.draggable = false;
  }

  else if (key === 'decrement') {
    const index = paletteImage.value.getIndex(mousePosition.value.x, mousePosition.value.y);
    if (index == 0) {
      return;
    }
    editMode.value = true;
    increment.value = false;
    drawIndex.value = index;
    stageConfig.value.draggable = false;
  }

  showDropdown.value = false;
}

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