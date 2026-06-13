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

      <!-- 摄像头截图与压缩区域 -->
      <section class="capture-section">
        <h2>摄像头截图与压缩</h2>
        <p class="capture-privacy-hint">
          摄像头视频不会持续上传。只有用户主动截图时，页面才会处理当前画面，并在上传前进行压缩。
        </p>
        <div class="capture-status" :class="`capture-status-${captureStatus}`">
          {{ captureStatusText }}
        </div>
        <div class="capture-controls">
          <button
            class="btn-primary"
            @click="captureCurrentFrame"
            :disabled="!isCameraActive || captureStatus === 'capturing'"
          >
            截取当前画面
          </button>
          <button
            class="btn-secondary"
            @click="clearCapturedImage"
            :disabled="!capturedImageBlob && !capturedImagePreviewUrl"
          >
            清除截图
          </button>
        </div>
        <div v-if="!isCameraActive" class="capture-warning">
          请先打开摄像头，再进行截图。
        </div>
        <div v-if="captureError" class="capture-error">
          {{ captureError }}
        </div>
        <div v-if="capturedImagePreviewUrl" class="capture-preview">
          <h3>截图预览</h3>
          <img
            :src="capturedImagePreviewUrl"
            alt="摄像头截图"
            class="capture-preview-image"
          />
          <div v-if="capturedImageMetadata" class="capture-metadata">
            <div class="capture-meta-row">
              <span class="capture-meta-label">原始尺寸：</span>
              <span>{{ capturedImageMetadata.originalWidth }} × {{ capturedImageMetadata.originalHeight }} px</span>
            </div>
            <div class="capture-meta-row">
              <span class="capture-meta-label">压缩后尺寸：</span>
              <span>{{ capturedImageMetadata.compressedWidth }} × {{ capturedImageMetadata.compressedHeight }} px</span>
            </div>
            <div class="capture-meta-row">
              <span class="capture-meta-label">文件大小：</span>
              <span>{{ formatFileSize(capturedImageMetadata.compressedSize) }}</span>
            </div>
            <div class="capture-meta-row">
              <span class="capture-meta-label">图片类型：</span>
              <span>{{ capturedImageMetadata.mimeType }}</span>
            </div>
            <div class="capture-meta-row">
              <span class="capture-meta-label">截图时间：</span>
              <span>{{ capturedImageMetadata.capturedAt }}</span>
            </div>
          </div>
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

      <!-- 视觉对话请求提交区域 -->
      <section class="dialogue-section">
        <h2>视觉对话请求</h2>
        <p class="dialogue-privacy-hint">
          图片仅在用户主动提交时发送到后端。后端会调用火山方舟 Coding Plan Doubao-Seed-2.0-Pro 视觉模型，并将真实回答返回。
        </p>
        <div class="dialogue-status" :class="`dialogue-status-${dialogueStatus}`">
          {{ dialogueStatusText }}
        </div>
        <div class="dialogue-controls">
          <button
            class="btn-primary"
            @click="submitVisualQuestion"
            :disabled="dialogueStatus === 'submitting' || !capturedImageBlob"
          >
            提交视觉问题
          </button>
        </div>
        <div v-if="dialogueStatus === 'submitting'" class="dialogue-info">
          AI 正在分析当前画面……
        </div>
        <div v-if="dialogueError" class="dialogue-error">
          {{ dialogueError }}
        </div>
        <div v-if="dialogueResult" class="dialogue-result">
          <div v-if="dialogueResult.status === 'success'" class="dialogue-result-notice success">
            AI 已完成视觉分析
          </div>
          <div v-if="dialogueResult.answer" class="dialogue-answer">
            <h3>AI 视觉回答</h3>
            <div class="dialogue-answer-text">{{ dialogueResult.answer }}</div>
            <div class="dialogue-speech-controls">
              <div class="dialogue-speech-status" :class="`dialogue-speech-status-${ttsStatus}`">
                语音状态：{{ ttsStatusText }}
              </div>
              <div class="dialogue-speech-buttons">
                <button
                  class="btn-primary btn-small"
                  @click="speakCurrentAnswer"
                  :disabled="!speechSynthesisSupported || !dialogueResult.answer || isSpeaking"
                >
                  朗读回答
                </button>
                <button
                  class="btn-secondary btn-small"
                  @click="stopSpeaking"
                  :disabled="!isSpeaking"
                >
                  停止朗读
                </button>
                <label class="dialogue-speech-toggle">
                  <input
                    type="checkbox"
                    v-model="autoSpeakEnabled"
                  />
                  <span>自动朗读 AI 回答</span>
                </label>
              </div>
              <div v-if="!speechSynthesisSupported" class="dialogue-speech-warn">
                当前浏览器不支持语音合成，请使用最新版 Chrome 或 Edge。
              </div>
              <div v-if="ttsError" class="dialogue-speech-error">
                {{ ttsError }}
              </div>
            </div>
          </div>
          <div v-if="dialogueResult.model" class="dialogue-meta-row">
            <span class="dialogue-meta-label">模型：</span>
            <span>{{ dialogueResult.model }}</span>
          </div>
          <div v-if="dialogueResult.request_id" class="dialogue-meta-row">
            <span class="dialogue-meta-label">request_id：</span>
            <span>{{ dialogueResult.request_id }}</span>
          </div>
          <div v-if="dialogueResult.image" class="dialogue-meta-row">
            <span class="dialogue-meta-label">图片大小：</span>
            <span>{{ formatFileSize(dialogueResult.image.size_bytes) }}</span>
          </div>
          <div v-if="dialogueResult.usage" class="dialogue-meta-row">
            <span class="dialogue-meta-label">Token 使用：</span>
            <span>
              提示 {{ dialogueResult.usage.prompt_tokens }} / 完成 {{ dialogueResult.usage.completion_tokens }} / 合计 {{ dialogueResult.usage.total_tokens }}
            </span>
          </div>
        </div>
      </section>

      <section class="features">
        <h2>核心功能（开发中）</h2>
        <ul>
          <li>✅ 项目骨架初始化</li>
          <li>✅ 摄像头调用（已完成）</li>
          <li>✅ 麦克风调用（已完成）</li>
          <li>✅ 语音识别（已完成）</li>
          <li>✅ 摄像头截图与前端压缩（已完成）</li>
          <li>✅ 视觉对话请求链路（已完成）</li>
          <li>✅ 视觉识别（已完成 - Doubao-Seed-2.0-Pro）</li>
          <li>✅ AI 回复生成（已完成）</li>
          <li>✅ 语音合成（已完成 - 浏览器原生 SpeechSynthesis）</li>
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

// ===== 图片压缩常量 =====
const MAX_IMAGE_DIMENSION = 1280
const JPEG_QUALITY = 0.75
const COMPRESSED_MIME_TYPE = 'image/jpeg'

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

// ===== 截图与压缩相关状态 =====
const captureStatus = ref('idle') // idle, capturing, completed, failed
const captureError = ref('')
const capturedImageBlob = ref(null)
const capturedImagePreviewUrl = ref('')
const capturedImageMetadata = ref(null)

const captureStatusText = computed(() => {
  const statusMap = {
    idle: '尚未截图',
    capturing: '正在截取并压缩画面……',
    completed: '画面已准备，可供后续视觉问答使用',
    failed: '截图失败，请重试'
  }
  return statusMap[captureStatus.value] || ''
})

// 工具：将文件大小转成易读格式
const formatFileSize = (bytes) => {
  if (typeof bytes !== 'number' || isNaN(bytes) || bytes < 0) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

// 工具：释放旧 Object URL，避免内存泄漏
const revokePreviewUrl = () => {
  if (capturedImagePreviewUrl.value) {
    try {
      URL.revokeObjectURL(capturedImagePreviewUrl.value)
    } catch (e) {
      console.error('Failed to revoke object URL:', e)
    }
    capturedImagePreviewUrl.value = ''
  }
}

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

// ===== 截图与压缩方法 =====
const captureCurrentFrame = async () => {
  captureError.value = ''

  if (!isCameraActive.value) {
    captureError.value = '请先打开摄像头，再进行截图。'
    captureStatus.value = 'failed'
    return
  }

  const video = videoElement.value
  if (!video || video.readyState < 2) {
    captureError.value = '摄像头尚未准备完成，请稍候再试。'
    captureStatus.value = 'failed'
    return
  }

  const originalWidth = video.videoWidth
  const originalHeight = video.videoHeight
  if (!originalWidth || !originalHeight) {
    captureError.value = '无法读取当前画面尺寸，请重试。'
    captureStatus.value = 'failed'
    return
  }

  captureStatus.value = 'capturing'

  try {
    // 计算压缩后尺寸：保持比例，最长边不超过 MAX_IMAGE_DIMENSION
    let targetWidth = originalWidth
    let targetHeight = originalHeight
    const longestSide = Math.max(originalWidth, originalHeight)
    if (longestSide > MAX_IMAGE_DIMENSION) {
      const scale = MAX_IMAGE_DIMENSION / longestSide
      targetWidth = Math.round(originalWidth * scale)
      targetHeight = Math.round(originalHeight * scale)
    }

    // 离屏 canvas 绘制当前帧
    const canvas = document.createElement('canvas')
    canvas.width = targetWidth
    canvas.height = targetHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      throw new Error('无法创建 canvas 2D 上下文')
    }
    ctx.drawImage(video, 0, 0, targetWidth, targetHeight)

    // 使用 toBlob 输出 JPEG
    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        (result) => {
          if (result) resolve(result)
          else reject(new Error('canvas.toBlob 返回空结果'))
        },
        COMPRESSED_MIME_TYPE,
        JPEG_QUALITY
      )
    })

    // 释放旧预览 URL，避免内存泄漏
    revokePreviewUrl()

    const previewUrl = URL.createObjectURL(blob)

    capturedImageBlob.value = blob
    capturedImagePreviewUrl.value = previewUrl
    capturedImageMetadata.value = {
      originalWidth,
      originalHeight,
      compressedWidth: targetWidth,
      compressedHeight: targetHeight,
      compressedSize: blob.size,
      mimeType: blob.type || COMPRESSED_MIME_TYPE,
      capturedAt: new Date().toLocaleString('zh-CN')
    }
    captureStatus.value = 'completed'
  } catch (error) {
    console.error('Capture failed:', error)
    captureError.value = '截图失败：' + (error && error.message ? error.message : '未知错误')
    captureStatus.value = 'failed'
  }
}

const clearCapturedImage = () => {
  revokePreviewUrl()
  capturedImageBlob.value = null
  capturedImageMetadata.value = null
  captureError.value = ''
  captureStatus.value = 'idle'
}

// ===== 视觉对话请求相关状态 =====
const dialogueStatus = ref('idle') // idle, submitting, success, failed
const dialogueError = ref('')
const dialogueResult = ref(null)

const dialogueStatusText = computed(() => {
  const statusMap = {
    idle: '尚未提交',
    submitting: 'AI 正在分析当前画面……',
    success: 'AI 已完成视觉分析',
    failed: '提交失败'
  }
  return statusMap[dialogueStatus.value] || ''
})

const submitVisualQuestion = async () => {
  dialogueError.value = ''
  dialogueResult.value = null

  // 校验截图
  if (!capturedImageBlob.value) {
    dialogueError.value = '请先打开摄像头并截取当前画面。'
    dialogueStatus.value = 'failed'
    return
  }

  // 校验问题（去空格后非空）
  const questionClean = (userQuestionText.value || '').trim()
  if (!questionClean) {
    dialogueError.value = '请先通过语音识别或手动输入问题。'
    dialogueStatus.value = 'failed'
    return
  }

  // 开始新请求前，先停止可能正在播放的旧语音，避免与新回答重叠
  if (isSpeaking.value) {
    stopSpeaking()
  }

  dialogueStatus.value = 'submitting'

  try {
    const formData = new FormData()
    formData.append('question', questionClean)
    // 给 Blob 起一个文件名，方便后端使用
    const filename = `snapshot.${capturedImageMetadata.value?.mimeType === 'image/png' ? 'png' : 'jpg'}`
    formData.append('image', capturedImageBlob.value, filename)

    const response = await fetch('/api/vision-dialogue', {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      // 优先展示后端 detail
      let detail = ''
      try {
        const data = await response.json()
        detail = data && data.detail ? data.detail : ''
      } catch (e) {
        // 后端没返回 JSON，忽略
      }
      throw new Error(detail || `请求失败（HTTP ${response.status}）`)
    }

    const data = await response.json()
    dialogueResult.value = data
    dialogueStatus.value = 'success'

    // 成功后，如果开启自动朗读，则朗读新回答
    if (autoSpeakEnabled.value && data && data.answer) {
      // 用 nextTick 确保 DOM 更新后再朗读（避免影响页面状态）
      try {
        speakText(data.answer)
      } catch (e) {
        // 朗读失败不影响文字回答
        console.error('Auto speak failed:', e)
      }
    }
  } catch (error) {
    console.error('Submit visual question failed:', error)
    if (error && error.name === 'TypeError' && /fetch/i.test(error.message || '')) {
      dialogueError.value = '网络异常，无法连接后端服务。请确认后端已启动（http://localhost:3001）。'
    } else {
      dialogueError.value = '提交失败：' + (error && error.message ? error.message : '未知错误')
    }
    dialogueStatus.value = 'failed'
  }
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

// ===== 语音合成（朗读 AI 回答）相关状态 =====
const ttsStatus = ref('idle') // idle, speaking, done, stopped, failed, unsupported
const ttsError = ref('')
const isSpeaking = ref(false)
const autoSpeakEnabled = ref(true)

// 检测浏览器是否支持 SpeechSynthesis
const speechSynthesisSupported = computed(
  () => typeof window !== 'undefined' && typeof window.speechSynthesis !== 'undefined'
)

const ttsStatusText = computed(() => {
  if (!speechSynthesisSupported.value) {
    return '浏览器不支持语音合成'
  }
  const statusMap = {
    idle: '未朗读',
    speaking: '正在朗读',
    done: '已完成',
    stopped: '已停止',
    failed: '朗读失败',
    unsupported: '浏览器不支持语音合成'
  }
  return statusMap[ttsStatus.value] || ''
})

// 缓存语音列表和已选中的中文 voice
let ttsVoices = []
let ttsZhVoice = null
let ttsVoicesLoaded = false

// 选择最合适的中文 voice
const pickZhVoice = (voices) => {
  if (!voices || voices.length === 0) return null
  // 优先 zh-CN（普通话）
  const zhCn = voices.find((v) => (v.lang || '').toLowerCase() === 'zh-cn')
  if (zhCn) return zhCn
  // 其次任意中文 lang 前缀
  const zhAny = voices.find((v) => (v.lang || '').toLowerCase().startsWith('zh'))
  if (zhAny) return zhAny
  // 退而求其次：默认（让浏览器自己决定）
  return null
}

const loadVoices = () => {
  if (!speechSynthesisSupported.value) return
  try {
    ttsVoices = window.speechSynthesis.getVoices() || []
    ttsVoicesLoaded = true
    ttsZhVoice = pickZhVoice(ttsVoices)
  } catch (e) {
    console.error('Failed to load voices:', e)
  }
}

// 某些浏览器需要监听 voiceschanged 才会填充
let ttsVoicesListener = null

if (speechSynthesisSupported.value) {
  loadVoices()
  if (typeof window.speechSynthesis.onvoiceschanged !== 'undefined') {
    ttsVoicesListener = () => loadVoices()
    try {
      window.speechSynthesis.onvoiceschanged = ttsVoicesListener
    } catch (e) {
      // 某些实现不支持 onvoiceschanged 赋值，忽略
    }
  }
}

// 当前正在朗读的 utterance（用于停止）
let ttsUtterance = null

const speakText = (text) => {
  ttsError.value = ''

  if (!speechSynthesisSupported.value) {
    ttsStatus.value = 'unsupported'
    ttsError.value = '当前浏览器不支持语音合成。'
    return
  }

  const cleanText = (text || '').toString().trim()
  if (!cleanText) {
    ttsError.value = '没有可朗读的内容。'
    ttsStatus.value = 'failed'
    return
  }

  // 每次开始新朗读前，先停止可能仍在播放的旧内容
  try {
    window.speechSynthesis.cancel()
  } catch (e) {
    console.error('Failed to cancel previous speech:', e)
  }

  // 部分浏览器 cancel 后立即 speak 会失败，加一点重试
  const trySpeak = (retries) => {
    try {
      const u = new SpeechSynthesisUtterance(cleanText)
      u.lang = 'zh-CN'
      u.rate = 1
      u.pitch = 1
      u.volume = 1
      // 选择已缓存的 voice
      if (ttsZhVoice) {
        try { u.voice = ttsZhVoice } catch (e) { /* noop */ }
      }

      u.onstart = () => {
        isSpeaking.value = true
        ttsStatus.value = 'speaking'
        ttsError.value = ''
      }

      u.onend = () => {
        isSpeaking.value = false
        ttsUtterance = null
        // 如果是被外部 cancel 触发的 onend，状态会保留为 stopped；否则正常完成
        if (ttsStatus.value !== 'stopped') {
          ttsStatus.value = 'done'
        }
      }

      u.onerror = (event) => {
        isSpeaking.value = false
        ttsUtterance = null
        const errCode = (event && event.error) || 'unknown'
        // canceled 是用户主动停止，不要当错误
        if (errCode === 'canceled' || errCode === 'interrupted') {
          if (ttsStatus.value !== 'stopped') {
            ttsStatus.value = 'stopped'
          }
          return
        }
        console.error('Speech synthesis error:', errCode)
        ttsError.value = '语音朗读失败：' + errCode
        ttsStatus.value = 'failed'
      }

      ttsUtterance = u
      window.speechSynthesis.speak(u)
    } catch (e) {
      if (retries > 0) {
        // 极少数浏览器 cancel 后立即 speak 抛 InvalidStateError，重试一次
        setTimeout(() => trySpeak(retries - 1), 50)
      } else {
        console.error('Speak failed:', e)
        ttsError.value = '语音朗读启动失败：' + (e && e.message ? e.message : '未知错误')
        ttsStatus.value = 'failed'
        isSpeaking.value = false
      }
    }
  }

  trySpeak(2)
}

const speakCurrentAnswer = () => {
  const answer = dialogueResult.value && dialogueResult.value.answer
  if (!answer) {
    ttsError.value = '当前没有可朗读的 AI 回答。'
    ttsStatus.value = 'failed'
    return
  }
  speakText(answer)
}

const stopSpeaking = () => {
  if (!speechSynthesisSupported.value) return
  try {
    window.speechSynthesis.cancel()
  } catch (e) {
    console.error('Failed to cancel speech:', e)
  }
  isSpeaking.value = false
  ttsUtterance = null
  // 只有在原本是 speaking 状态时才标 stopped
  if (ttsStatus.value === 'speaking') {
    ttsStatus.value = 'stopped'
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
  // 释放截图预览 URL，避免内存泄漏
  revokePreviewUrl()
  // 停止任何正在播放的语音
  if (speechSynthesisSupported.value) {
    try { window.speechSynthesis.cancel() } catch (e) { /* noop */ }
  }
  // 移除 voiceschanged 监听
  if (ttsVoicesListener && speechSynthesisSupported.value) {
    try {
      window.speechSynthesis.onvoiceschanged = null
    } catch (e) {
      // noop
    }
    ttsVoicesListener = null
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

/* 截图与压缩区域样式 */
.capture-section {
  text-align: left;
}

.capture-privacy-hint {
  font-size: 0.9rem;
  opacity: 0.9;
  margin: 0 0 1rem 0;
  padding: 0.6rem 0.9rem;
  background: rgba(78, 205, 196, 0.15);
  border-left: 3px solid rgba(78, 205, 196, 0.7);
  border-radius: 4px;
}

.capture-status {
  display: inline-block;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: 1rem;
  background: rgba(255, 255, 255, 0.15);
}

.capture-status-idle {
  background: rgba(255, 255, 255, 0.15);
}

.capture-status-capturing {
  background: rgba(78, 205, 196, 0.4);
  color: #fff;
}

.capture-status-completed {
  background: rgba(102, 187, 106, 0.5);
  color: #fff;
}

.capture-status-failed {
  background: rgba(255, 107, 107, 0.5);
  color: #fff;
}

.capture-controls {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.capture-warning {
  background: rgba(255, 193, 7, 0.15);
  border: 1px solid rgba(255, 193, 7, 0.4);
  color: #ffe8a1;
  padding: 0.5rem 0.85rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.capture-error {
  background: rgba(255, 107, 107, 0.2);
  border: 1px solid rgba(255, 107, 107, 0.5);
  color: #ffd1d1;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.95rem;
}

.capture-preview {
  margin-top: 1.25rem;
}

.capture-preview h3 {
  font-size: 1.05rem;
  margin: 0 0 0.5rem 0;
  color: #fff;
}

.capture-preview-image {
  display: block;
  width: 100%;
  max-width: 480px;
  height: auto;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  margin-bottom: 1rem;
}

.capture-metadata {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  padding: 0.85rem 1rem;
  font-size: 0.92rem;
  line-height: 1.7;
}

.capture-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.capture-meta-label {
  color: #4ecdc4;
  font-weight: 500;
  min-width: 7rem;
}

/* 视觉对话请求区域样式 */
.dialogue-section {
  text-align: left;
}

.dialogue-privacy-hint {
  font-size: 0.9rem;
  opacity: 0.9;
  margin: 0 0 1rem 0;
  padding: 0.6rem 0.9rem;
  background: rgba(78, 205, 196, 0.15);
  border-left: 3px solid rgba(78, 205, 196, 0.7);
  border-radius: 4px;
}

.dialogue-status {
  display: inline-block;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: 1rem;
  background: rgba(255, 255, 255, 0.15);
}

.dialogue-status-idle {
  background: rgba(255, 255, 255, 0.15);
}

.dialogue-status-submitting {
  background: rgba(78, 205, 196, 0.4);
  color: #fff;
}

.dialogue-status-success {
  background: rgba(102, 187, 106, 0.5);
  color: #fff;
}

.dialogue-status-failed {
  background: rgba(255, 107, 107, 0.5);
  color: #fff;
}

.dialogue-controls {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.dialogue-info {
  background: rgba(78, 205, 196, 0.15);
  border: 1px solid rgba(78, 205, 196, 0.4);
  color: #c5f0ec;
  padding: 0.6rem 0.9rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.95rem;
}

.dialogue-error {
  background: rgba(255, 107, 107, 0.2);
  border: 1px solid rgba(255, 107, 107, 0.5);
  color: #ffd1d1;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.95rem;
}

.dialogue-result {
  margin-top: 1.25rem;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  padding: 0.85rem 1rem;
  font-size: 0.92rem;
  line-height: 1.7;
}

.dialogue-result-notice {
  font-weight: 500;
  color: #ffe8a1;
  background: rgba(255, 193, 7, 0.15);
  border-left: 3px solid rgba(255, 193, 7, 0.7);
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  margin-bottom: 0.85rem;
}

.dialogue-result-notice.success {
  color: #c8f7c5;
  background: rgba(102, 187, 106, 0.2);
  border-left-color: rgba(102, 187, 106, 0.85);
}

.dialogue-answer {
  margin: 0.85rem 0;
  padding: 0.75rem 1rem;
  background: rgba(78, 205, 196, 0.12);
  border-left: 3px solid rgba(78, 205, 196, 0.7);
  border-radius: 4px;
}

.dialogue-answer h3 {
  margin: 0 0 0.4rem 0;
  font-size: 1rem;
  color: #4ecdc4;
}

.dialogue-answer-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  font-size: 0.95rem;
}

/* PR7: AI 回答语音合成朗读控件 */
.dialogue-speech-controls {
  margin-top: 0.85rem;
  padding-top: 0.75rem;
  border-top: 1px dashed rgba(255, 255, 255, 0.18);
}

.dialogue-speech-status {
  display: inline-block;
  padding: 0.25rem 0.7rem;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 500;
  margin-bottom: 0.6rem;
  background: rgba(255, 255, 255, 0.12);
  color: #e6f1ff;
}

.dialogue-speech-status-idle {
  background: rgba(255, 255, 255, 0.12);
}

.dialogue-speech-status-speaking {
  background: rgba(78, 205, 196, 0.45);
  color: #fff;
}

.dialogue-speech-status-done {
  background: rgba(102, 187, 106, 0.45);
  color: #fff;
}

.dialogue-speech-status-stopped {
  background: rgba(255, 193, 7, 0.4);
  color: #fff;
}

.dialogue-speech-status-failed,
.dialogue-speech-status-unsupported {
  background: rgba(255, 107, 107, 0.4);
  color: #fff;
}

.dialogue-speech-buttons {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.btn-small {
  padding: 0.4rem 0.85rem;
  font-size: 0.9rem;
}

.dialogue-speech-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.9rem;
  cursor: pointer;
  user-select: none;
  color: #e6f1ff;
}

.dialogue-speech-toggle input {
  cursor: pointer;
}

.dialogue-speech-warn {
  margin-top: 0.5rem;
  font-size: 0.88rem;
  color: #ffd1d1;
  background: rgba(255, 107, 107, 0.18);
  border: 1px solid rgba(255, 107, 107, 0.4);
  padding: 0.45rem 0.7rem;
  border-radius: 4px;
}

.dialogue-speech-error {
  margin-top: 0.5rem;
  font-size: 0.88rem;
  color: #ffd1d1;
  background: rgba(255, 107, 107, 0.15);
  border: 1px solid rgba(255, 107, 107, 0.35);
  padding: 0.45rem 0.7rem;
  border-radius: 4px;
}

.dialogue-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.2rem;
}

.dialogue-meta-label {
  color: #4ecdc4;
  font-weight: 500;
  min-width: 7rem;
}

.dialogue-meta-hash {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  background: rgba(0, 0, 0, 0.3);
  padding: 0.05rem 0.4rem;
  border-radius: 3px;
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
