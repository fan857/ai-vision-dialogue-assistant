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

      <!-- 麦克风语音识别区域 -->
      <section class="voice-section">
        <h2>麦克风语音识别</h2>
        <p class="voice-hint">
          浏览器将使用 Web Speech API 进行中文语音识别，识别结果会显示在下方。
        </p>
        <div class="voice-status" :class="`voice-status-${speechStatus}`">
          状态：{{ speechStatusText }}
        </div>
        <div class="voice-controls">
          <button
            class="btn-primary"
            @click="startSpeechRecognition"
            :disabled="!speechSupported || speechStatus === 'requesting' || speechStatus === 'recognizing'"
          >
            开始语音识别
          </button>
          <button
            class="btn-secondary"
            @click="stopSpeechRecognition"
            :disabled="speechStatus !== 'recognizing' && speechStatus !== 'requesting'"
          >
            停止识别
          </button>
        </div>
        <div v-if="speechError" class="voice-error">
          {{ speechError }}
        </div>
        <div class="voice-result">
          <h3>识别到的问题</h3>
          <div class="voice-result-text">
            {{ userQuestionText || '（暂无识别结果）' }}
          </div>
        </div>
        <div class="voice-fallback">
          <h3>手动输入（fallback）</h3>
          <p class="voice-fallback-hint">
            如果浏览器不支持语音识别或识别失败，可以手动输入问题文本。
          </p>
          <textarea
            v-model="userQuestionText"
            class="voice-textarea"
            rows="3"
            placeholder="请输入你想问 AI 的问题..."
          ></textarea>
        </div>
      </section>

      <section class="features">
        <h2>核心功能（开发中）</h2>
        <ul>
          <li>✅ 项目骨架初始化</li>
          <li>✅ 摄像头调用（已完成）</li>
          <li>✅ 麦克风调用（已完成）</li>
          <li>✅ 语音识别（已完成）</li>
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

// ===== 摄像头相关状态 =====
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

// ===== 语音识别相关状态 =====
const speechStatus = ref('idle') // idle, requesting, recognizing, completed, failed, unsupported
const speechError = ref('')
const userQuestionText = ref('')

const SpeechRecognitionCtor =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null
const speechSupported = computed(() => !!SpeechRecognitionCtor)

const speechStatusText = computed(() => {
  if (!speechSupported.value) {
    return '浏览器不支持 Web Speech API'
  }
  const statusMap = {
    idle: '未开始',
    requesting: '正在请求麦克风/语音识别权限...',
    recognizing: '正在识别，请说话...',
    completed: '识别完成',
    failed: '识别失败',
    unsupported: '浏览器不支持 Web Speech API'
  }
  return statusMap[speechStatus.value] || ''
})

let recognition = null

// ===== 摄像头方法 =====
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

// ===== 语音识别方法 =====
const startSpeechRecognition = () => {
  speechError.value = ''

  if (!SpeechRecognitionCtor) {
    speechStatus.value = 'unsupported'
    speechError.value = '当前浏览器不支持 Web Speech API，请使用 Chrome / Edge 等浏览器或使用下方手动输入。'
    return
  }

  try {
    if (recognition) {
      try { recognition.abort() } catch (e) { /* noop */ }
    }

    const recognizer = new SpeechRecognitionCtor()
    recognizer.lang = 'zh-CN'
    recognizer.continuous = false
    recognizer.interimResults = true

    recognizer.onstart = () => {
      speechStatus.value = 'recognizing'
      speechError.value = ''
    }

    recognizer.onresult = (event) => {
      let finalTranscript = ''
      let interimTranscript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          finalTranscript += result[0].transcript
        } else {
          interimTranscript += result[0].transcript
        }
      }
      if (finalTranscript) {
        userQuestionText.value = finalTranscript.trim()
        speechStatus.value = 'completed'
      } else if (interimTranscript) {
        userQuestionText.value = interimTranscript.trim()
      }
    }

    recognizer.onerror = (event) => {
      console.error('Speech recognition error:', event.error)
      const errorType = event.error || 'unknown'
      let message = '语音识别失败，请重试。'
      if (errorType === 'not-allowed' || errorType === 'service-not-allowed') {
        message = '麦克风权限被拒绝，请在浏览器设置中允许使用麦克风。'
      } else if (errorType === 'no-speech') {
        message = '未检测到语音，请重试并确保麦克风工作正常。'
      } else if (errorType === 'audio-capture') {
        message = '无法获取麦克风，请检查设备是否可用。'
      } else if (errorType === 'network') {
        message = '网络错误，语音识别需要联网，请检查网络后重试。'
      } else if (errorType === 'aborted') {
        message = ''
      }
      speechError.value = message
      speechStatus.value = 'failed'
    }

    recognizer.onend = () => {
      if (speechStatus.value === 'recognizing') {
        speechStatus.value = 'completed'
      }
      recognition = null
    }

    recognition = recognizer
    speechStatus.value = 'requesting'
    recognizer.start()
  } catch (error) {
    console.error('Failed to start speech recognition:', error)
    speechStatus.value = 'failed'
    speechError.value = '启动语音识别失败：' + (error && error.message ? error.message : '未知错误')
  }
}

const stopSpeechRecognition = () => {
  if (recognition) {
    try {
      recognition.stop()
    } catch (e) {
      console.error('Error stopping recognition:', e)
    }
  }
  if (speechStatus.value === 'recognizing' || speechStatus.value === 'requesting') {
    speechStatus.value = 'completed'
  }
}

// ===== 生命周期 =====
onBeforeUnmount(() => {
  if (isCameraActive.value) {
    stopCamera()
  }
  if (recognition) {
    try { recognition.abort() } catch (e) { /* noop */ }
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

/* 语音识别区域样式 */
.voice-section {
  text-align: left;
}

.voice-hint {
  font-size: 0.95rem;
  opacity: 0.9;
  margin: 0 0 1rem 0;
}

.voice-status {
  display: inline-block;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: 1rem;
  background: rgba(255, 255, 255, 0.15);
}

.voice-status-idle {
  background: rgba(255, 255, 255, 0.15);
}

.voice-status-requesting,
.voice-status-recognizing {
  background: rgba(78, 205, 196, 0.4);
  color: #fff;
}

.voice-status-completed {
  background: rgba(102, 187, 106, 0.5);
  color: #fff;
}

.voice-status-failed,
.voice-status-unsupported {
  background: rgba(255, 107, 107, 0.5);
  color: #fff;
}

.voice-controls {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.voice-error {
  background: rgba(255, 107, 107, 0.2);
  border: 1px solid rgba(255, 107, 107, 0.5);
  color: #ffd1d1;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.95rem;
}

.voice-result,
.voice-fallback {
  margin-top: 1.25rem;
}

.voice-result h3,
.voice-fallback h3 {
  font-size: 1.05rem;
  margin: 0 0 0.5rem 0;
  color: #fff;
}

.voice-result-text {
  min-height: 3rem;
  padding: 0.75rem 1rem;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}

.voice-fallback-hint {
  font-size: 0.85rem;
  opacity: 0.85;
  margin: 0 0 0.5rem 0;
}

.voice-textarea {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  font-family: inherit;
  background: rgba(0, 0, 0, 0.25);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  resize: vertical;
  box-sizing: border-box;
}

.voice-textarea::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.voice-textarea:focus {
  outline: none;
  border-color: rgba(78, 205, 196, 0.7);
  box-shadow: 0 0 0 2px rgba(78, 205, 196, 0.2);
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

.btn-secondary {
  padding: 0.75rem 2rem;
  font-size: 1.1rem;
  background: rgba(255, 255, 255, 0.15);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, background 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  background: rgba(255, 255, 255, 0.25);
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary:active:not(:disabled) {
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
