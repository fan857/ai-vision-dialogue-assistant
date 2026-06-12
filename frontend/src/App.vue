<template>
  <div class="app">
    <header class="header">
      <h1 class="title">AI 视觉对话助手</h1>
      <p class="subtitle">基于七牛云的智能视觉对话应用</p>
    </header>
    
    <main class="main">
      <section class="intro">
        <h2>项目概述</h2>
        <p>
          这是一个 AI 视觉对话助手应用，用户可以通过摄像头和麦克风与 AI 进行交互。
          AI 能够理解摄像头中的视觉内容和用户的语音提问，并提供恰当的回应。
        </p>
      </section>

      <!-- 摄像头预览区域 -->
      <section class="camera-section">
        <h2>摄像头预览</h2>
        <div class="camera-container">
          <video 
            ref="videoElement" 
            class="camera-preview" 
            autoplay 
            playsinline
            :class="{ 'hidden': !isCameraActive }"
          ></video>
          <div v-if="!isCameraActive && cameraStatus !== 'failed'" class="camera-placeholder">
            {{ cameraStatusText }}
          </div>
          <div v-if="cameraStatus === 'failed'" class="camera-error">
            {{ cameraStatusText }}
          </div>
        </div>
        <div class="camera-controls">
          <button 
            class="btn-primary" 
            @click="toggleCamera"
            :disabled="cameraStatus === 'requesting'"
          >
            {{ isCameraActive ? '关闭摄像头' : '打开摄像头' }}
          </button>
        </div>
      </section>
      
      <section class="features">
        <h2>核心功能（开发中）</h2>
        <ul>
          <li>✅ 项目骨架初始化</li>
          <li>✅ 摄像头调用（已完成）</li>
          <li>🔄 麦克风调用（开发中）</li>
          <li>🔄 语音识别（开发中）</li>
          <li>🔄 视觉识别（开发中）</li>
          <li>🔄 AI 回复生成（开发中）</li>
          <li>🔄 语音合成（开发中）</li>
        </ul>
      </section>

      <section class="project-structure">
        <h2>项目结构</h2>
        <pre><code>├── frontend/       # Vue3 + Vite 前端
├── backend/        # FastAPI 后端
├── docs/           # 设计文档
└── README.md       # 项目说明</code></pre>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'

const videoElement = ref(null)
const isCameraActive = ref(false)
const cameraStatus = ref('idle') // idle, requesting, active, failed

const cameraStatusText = computed(() => {
  const statusMap = {
    idle: '摄像头未开启，点击下方按钮开启',
    requesting: '正在请求摄像头权限...',
    active: '摄像头已开启',
    failed: '摄像头开启失败，请检查权限设置'
  }
  return statusMap[cameraStatus.value]
})

let mediaStream = null

const toggleCamera = async () => {
  if (isCameraActive.value) {
    await stopCamera()
  } else {
    await startCamera()
  }
}

const startCamera = async () => {
  try {
    cameraStatus.value = 'requesting'
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { 
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'user'
      },
      audio: false
    })
    
    if (videoElement.value) {
      videoElement.value.srcObject = mediaStream
      isCameraActive.value = true
      cameraStatus.value = 'active'
    }
  } catch (error) {
    console.error('Error accessing camera:', error)
    cameraStatus.value = 'failed'
    isCameraActive.value = false
  }
}

const stopCamera = async () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
    mediaStream = null
  }
  
  if (videoElement.value) {
    videoElement.value.srcObject = null
  }
  
  isCameraActive.value = false
  cameraStatus.value = 'idle'
}

onBeforeUnmount(() => {
  if (isCameraActive.value) {
    stopCamera()
  }
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.header {
  padding: 2rem;
  text-align: center;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.title {
  font-size: 2.5rem;
  margin: 0 0 1rem 0;
  font-weight: 700;
}

.subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
  margin: 0;
}

.main {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

h2 {
  font-size: 1.5rem;
  margin: 0 0 1rem 0;
  color: #fff;
}

p {
  line-height: 1.6;
  margin: 0 0 1rem 0;
}

/* 摄像头预览样式 */
.camera-section {
  text-align: center;
}

.camera-container {
  position: relative;
  width: 100%;
  max-width: 640px;
  margin: 0 auto 1rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  overflow: hidden;
  aspect-ratio: 16/9;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-placeholder,
.camera-error {
  position: absolute;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
  font-size: 1.1rem;
  background: rgba(0, 0, 0, 0.2);
}

.camera-error {
  color: #ff6b6b;
  font-weight: 500;
}

.hidden {
  display: none;
}

.camera-controls {
  margin-top: 1rem;
}

.btn-primary {
  padding: 0.75rem 2rem;
  font-size: 1.1rem;
  background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

li {
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

li:last-child {
  border-bottom: none;
}

pre {
  background: rgba(0, 0, 0, 0.2);
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
}

code {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

@media (max-width: 600px) {
  .title {
    font-size: 2rem;
  }
  
  .main {
    padding: 1rem;
  }
  
  section {
    padding: 1rem;
  }

  .camera-container {
    max-width: 100%;
  }
}
</style>
