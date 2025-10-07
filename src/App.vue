<script setup>
// 移除原有的组件引用
// import HelloWorld from './components/HelloWorld.vue'
// import TheWelcome from './components/TheWelcome.vue'
import Canva from './components/Canva.vue';
import Log from './components/Log.vue';
import Settings from './components/Settings.vue';
</script>

<template>
  <div class="container">
    <!-- 左侧画布区域 (80%) -->
    <div class="canvas-area">
      <Canva/>
    </div>
    
    <!-- 右侧控制区域 (20%) -->
    <div class="control-area">
      <!-- 上方配置区域 (70%) -->
      <div class="config-section">
        <Settings/>
      </div>
      
      <!-- 下方日志区域 (30%) -->
      <div class="log-section">
        <Log/>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 重置默认样式以确保全屏布局 */
:global(body), :global(html) {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
}

.container {
  display: flex;
  height: 100vh;
  width: 100vw; /* 使用视窗单位确保占满全宽 */
  position: fixed; /* 固定定位确保从左上角开始 */
  top: 0;
  left: 0;
}

.canvas-area {
  flex: 8;
  background-color: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.control-area {
  flex: 2;
  display: flex;
  flex-direction: column;
  background-color: #e0e0e0;
}

.config-section {
  flex: 6;
  background-color: #d0d0d0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.log-section {
  flex: 4;
  background-color: #c0c0c0;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
