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

      <!-- 实时语音视觉对话（PR8） -->
      <section class="realtime-section">
        <h2>实时语音视觉对话（Qwen3.5-Omni-Flash-Realtime + 豆包视觉）</h2>
        <p class="realtime-hint">
          点击「开始实时对话」后，浏览器会持续把麦克风音频通过 WebSocket 发送给后端，
          阿里云百炼 Qwen 实时识别你的问题。涉及画面时，Qwen 会自动调用豆包视觉工具分析当前画面。
          关闭会话立即停止音频上传和图片使用。
        </p>

        <div class="realtime-status-row">
          <span class="realtime-status-label">连接状态：</span>
          <span :class="['realtime-status-pill', `realtime-status-${realtimeStatus}`]">
            {{ realtimeStatusText }}
          </span>
        </div>

        <div v-if="realtimeVisionNote" class="realtime-vision-note">
          {{ realtimeVisionNote }}
        </div>

        <div class="realtime-controls">
          <button
            v-if="realtimeStatus === 'idle' || realtimeStatus === 'ended' || realtimeStatus === 'failed'"
            class="btn-primary"
            @click="startRealtimeSession"
            :disabled="!canStartRealtime"
          >
            开始实时对话
          </button>
          <button
            v-if="realtimeStatus !== 'idle' && realtimeStatus !== 'ended' && realtimeStatus !== 'failed'"
            class="btn-danger"
            @click="endRealtimeSession"
          >
            结束会话
          </button>
          <button
            v-if="realtimeStatus !== 'idle' && realtimeStatus !== 'ended' && realtimeStatus !== 'failed'"
            class="btn-secondary"
            @click="stopRealtimePlayback"
            :disabled="!isRealtimePlaying"
          >
            停止当前播放
          </button>
        </div>

        <div v-if="!canStartRealtime" class="realtime-warn">
          实时对话需要先打开摄像头（AudioWorklet 浏览器需支持）。摄像头未开启或浏览器不支持。
        </div>

        <div v-if="realtimeError" class="realtime-error">
          {{ realtimeError }}
        </div>

        <div class="realtime-conversation">
          <div v-if="realtimeCurrentFrameUrl" class="realtime-frame">
            <div class="realtime-frame-label">当前已截取画面（已发送给 AI）：</div>
            <img
              :src="realtimeCurrentFrameUrl"
              class="realtime-frame-image"
              alt="当前已截取并发送给 AI 的画面"
            >
          </div>
          <div class="realtime-transcript">
            <div class="realtime-transcript-label">你说：</div>
            <div class="realtime-transcript-text">
              {{ realtimeUserTranscript || '（等待开始说话…）' }}
            </div>
          </div>
          <div class="realtime-answer">
            <div class="realtime-answer-label">AI 回答：</div>
            <div class="realtime-answer-text">
              {{ realtimeAssistantText || '（等待 AI 回答…）' }}
            </div>
            <div v-if="isRealtimePlaying" class="realtime-playing-indicator">
              正在播放
              <span class="realtime-playing-dot"></span>
            </div>
          </div>
        </div>

        <p class="realtime-cost-hint">
          AI 回答使用浏览器原生流式播放（PCM 音频），不调用云端 TTS；不向 Qwen 发送图片；
          只有你点击「开始实时对话」期间才会上传音频；结束会话后立即停止。
          当实时功能不可用时，仍可使用上方「视觉问答」+「AI 回答语音合成」作为备用方案。
        </p>
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
          <li>✅ 实时语音视觉对话（已完成 - Qwen3.5-Omni-Flash-Realtime + 豆包视觉）</li>
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
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { PCMStreamPlayer } from './audio/pcm-player.js'

// ===== 图片压缩常量 =====
const MAX_IMAGE_DIMENSION = 1920
const JPEG_QUALITY = 0.92
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

// 工具：将毫秒数转成易读格式（PR9：缓存与耗时显示）
const formatDuration = (ms) => {
  if (typeof ms !== 'number' || isNaN(ms) || ms < 0) return '-'
  if (ms < 1000) return `${ms} 毫秒`
  return `${(ms / 1000).toFixed(2)} 秒`
}

// PR11: 实时对话区显示当前已截取画面（可视化确认传给后端的是哪一帧）
const realtimeCurrentFrameUrl = ref('')
watch(capturedImageBlob, (newBlob) => {
  if (realtimeCurrentFrameUrl.value) {
    URL.revokeObjectURL(realtimeCurrentFrameUrl.value)
    realtimeCurrentFrameUrl.value = ''
  }
  if (newBlob) {
    realtimeCurrentFrameUrl.value = URL.createObjectURL(newBlob)
  }
})

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

    // PR11: 不再生成预览图与元数据；只保存 Blob 供后续提交 / 实时对话复用
    capturedImageBlob.value = blob
    captureStatus.value = 'completed'
  } catch (error) {
    console.error('Capture failed:', error)
    captureError.value = '截图失败：' + (error && error.message ? error.message : '未知错误')
    captureStatus.value = 'failed'
  }
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
    const filename = `snapshot.${capturedImageBlob.value?.type === 'image/png' ? 'png' : 'jpg'}`
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

// ===== 实时语音视觉对话（PR8） =====
// 流程：开始会话 -> 把当前压缩截图和 session.init 发到后端 -> 后端连 Qwen Realtime
// -> 浏览器通过 AudioWorklet 采集 16kHz 16bit mono PCM 并通过 WebSocket 二进制帧上传
// -> Qwen 实时返回 user 转写 + AI 文本/音频 -> 浏览器用 PCMStreamPlayer 排队播放
// -> 涉及画面时 Qwen 调用 analyze_current_frame 工具 -> 后端复用 PR6 Doubao 视觉
const realtimeStatus = ref('idle') // idle, connecting, listening, recognizing, analyzing, answering, playing, ended, failed
const realtimeError = ref('')
const realtimeUserTranscript = ref('')
const realtimeAssistantText = ref('')
const isRealtimePlaying = ref(false)
const realtimeVisionNote = ref('')

const realtimeStatusText = computed(() => {
  const statusMap = {
    idle: '未开始',
    connecting: '正在连接 Qwen Realtime...',
    listening: '正在聆听，请说话...',
    recognizing: '正在识别...',
    analyzing: '正在分析当前画面（豆包视觉）...',
    answering: '正在回答...',
    playing: '正在播放 AI 回答',
    ended: '已结束',
    failed: '连接失败'
  }
  return statusMap[realtimeStatus.value] || ''
})

// 是否允许开始：需要打开摄像头 + AudioWorklet 支持
const audioWorkletSupported = computed(
  () => typeof window !== 'undefined' && typeof window.AudioWorklet !== 'undefined'
)
const canStartRealtime = computed(
  () => isCameraActive.value && audioWorkletSupported.value
)

// WebSocket / AudioContext / Worklet 节点
let realtimeWs = null
let realtimeAudioContext = null
let realtimeMicStream = null
let realtimeMicSource = null
let realtimeWorkletNode = null
let realtimePlayer = null
let realtimeHeartbeatTimer = null
let realtimeIntentionalClose = false

// WebSocket URL
const getRealtimeWsUrl = () => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  // Vite 开发代理会把 ws 转发到后端
  return `${proto}://${window.location.host}/ws/realtime-voice`
}

// 把 Blob 读取为 Base64（用于 session.init）
const blobToBase64 = (blob) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result || ''
      // result 是 "data:image/jpeg;base64,XXXX"
      const idx = typeof result === 'string' ? result.indexOf(',') : -1
      if (idx >= 0) {
        resolve(result.substring(idx + 1))
      } else {
        resolve('')
      }
    }
    reader.onerror = () => reject(reader.error || new Error('FileReader error'))
    reader.readAsDataURL(blob)
  })
}

// 拼接用户转写增量
const appendUserTranscript = (delta) => {
  if (!delta) return
  realtimeUserTranscript.value = (realtimeUserTranscript.value || '') + delta
}

// 拼接 AI 文本增量
const appendAssistantText = (delta) => {
  if (!delta) return
  realtimeAssistantText.value = (realtimeAssistantText.value || '') + delta
}

// PR11: 节流标记 —— 用户开口时立即截一帧并发给后端，保证 Qwen 调用视觉工具时图必到。
// 一句话内重复触发会被节流（避免短时间内发多张图），下一句重新允许。
let realtimeFrameInFlight = false

// 截图并发图：把当前帧发给后端（只发一次，不轮询）
const captureAndSendFrame = async (reason) => {
  if (realtimeFrameInFlight) return
  if (!isCameraActive.value) return
  if (!realtimeWs || realtimeWs.readyState !== 1) return
  realtimeFrameInFlight = true
  try {
    await captureCurrentFrame()
  } catch (e) {
    realtimeError.value = '自动截取画面失败：' + (e && e.message ? e.message : '未知错误')
    realtimeFrameInFlight = false
    return
  }
  if (!capturedImageBlob.value) {
    realtimeFrameInFlight = false
    return
  }
  try {
    const b64 = await blobToBase64(capturedImageBlob.value)
    realtimeWs.send(
      JSON.stringify({
        type: 'session.update_image',
        image_base64: b64,
        content_type: capturedImageBlob.value.type || 'image/jpeg'
      })
    )
  } catch (e) {
    console.error('send session.update_image failed:', e)
  } finally {
    // 给后端一点时间处理，避免极端情况下同一句话里发多张
    setTimeout(() => { realtimeFrameInFlight = false }, 400)
  }
}

// 启动：建立 WS、初始化 AudioWorklet + 麦克风（不预截图，等用户提问再按需截）
const startRealtimeSession = async () => {
  realtimeError.value = ''
  realtimeUserTranscript.value = ''
  realtimeAssistantText.value = ''

  if (!audioWorkletSupported.value) {
    realtimeError.value = '当前浏览器不支持 AudioWorklet，无法采集麦克风 PCM。'
    realtimeStatus.value = 'failed'
    return
  }

  realtimeStatus.value = 'connecting'
  realtimeIntentionalClose = false

  // 1) 准备 PCM 播放器
  try {
    if (!realtimePlayer) {
      realtimePlayer = new PCMStreamPlayer()
      realtimePlayer.onStateChange = (s) => {
        isRealtimePlaying.value = s
      }
    }
  } catch (e) {
    realtimeError.value = '初始化音频播放器失败：' + (e && e.message ? e.message : '未知错误')
    realtimeStatus.value = 'failed'
    return
  }

  // 2) 建立 WebSocket
  let ws
  try {
    ws = new WebSocket(getRealtimeWsUrl())
  } catch (e) {
    realtimeError.value = '无法创建 WebSocket：' + (e && e.message ? e.message : '未知错误')
    realtimeStatus.value = 'failed'
    return
  }
  realtimeWs = ws
  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    // PR11: 启动时不预截图，session.init 不带 image_base64。
    // 用户问完一个问题后，若命中视觉关键词再发 session.update_image 补图。
    try {
      ws.send(JSON.stringify({ type: 'session.init' }))
    } catch (e) {
      realtimeError.value = '发送 session.init 失败：' + (e && e.message ? e.message : '未知错误')
      realtimeStatus.value = 'failed'
      try { ws.close() } catch (err) { /* noop */ }
    }
  }

  ws.onmessage = async (event) => {
    if (event.data instanceof ArrayBuffer) {
      // 下行音频：24kHz 16bit mono PCM
      try {
        await realtimePlayer.push(new Uint8Array(event.data))
      } catch (e) {
        console.error('PCM push failed:', e)
      }
      return
    }
    let evt
    try {
      evt = JSON.parse(event.data)
    } catch (e) {
      return
    }
    const t = evt.type

    if (t === 'session.ready') {
      // 启动麦克风采集
      try {
        await startMicCapture()
        realtimeStatus.value = 'listening'
      } catch (e) {
        realtimeError.value = '启动麦克风失败：' + (e && e.message ? e.message : '未知错误')
        realtimeStatus.value = 'failed'
        endRealtimeSession()
      }
      return
    }

    if (t === 'session.error') {
      realtimeError.value = evt.message || '会话启动失败'
      realtimeStatus.value = 'failed'
      endRealtimeSession()
      return
    }

    if (t === 'server.disconnected') {
      realtimeStatus.value = 'ended'
      return
    }

    if (t === 'server.error') {
      console.error('Qwen realtime error:', evt.error)
      // 不立即 fail，让用户可以重试
      return
    }

    // 用户转写（Qwen Realtime 事件名）
    if (
      t === 'conversation.item.input_audio_transcription.delta' ||
      t === 'response.input_audio_transcription.delta'
    ) {
      realtimeStatus.value = 'recognizing'
      appendUserTranscript(evt.delta || '')
      // PR11: 用户开口就立即截一帧并发给后端 —— 在 Qwen 调用视觉工具前保证图必到
      captureAndSendFrame('delta')
      return
    }
    if (
      t === 'conversation.item.input_audio_transcription.completed' ||
      t === 'conversation.item.input_audio_transcription.done' ||
      t === 'response.input_audio_transcription.completed' ||
      t === 'response.input_audio_transcription.done'
    ) {
      const transcript = evt.transcript || evt.text || ''
      if (transcript && !realtimeUserTranscript.value.includes(transcript)) {
        appendUserTranscript(transcript)
      }
      return
    }

    // AI 文本
    if (t === 'response.audio_transcript.delta' || t === 'response.text.delta') {
      realtimeStatus.value = 'answering'
      appendAssistantText(evt.delta || '')
      return
    }
    if (
      t === 'response.audio_transcript.done' ||
      t === 'response.text.done' ||
      t === 'response.audio_transcript.completed' ||
      t === 'response.text.completed'
    ) {
      // 文本流结束：标记为 playing
      if (isRealtimePlaying.value) {
        realtimeStatus.value = 'playing'
      } else {
        realtimeStatus.value = 'listening'
      }
      return
    }

    // 工具调用 -> 视觉分析
    if (t === 'vision.analyzing') {
      realtimeStatus.value = 'analyzing'
      realtimeVisionNote.value = '正在分析当前画面（豆包视觉）...'
      return
    }
    if (t === 'vision.analyzed') {
      // 回到 answering
      realtimeStatus.value = 'answering'
      const hit = evt.cache_hit
      const source = evt.source
      if (hit) {
        realtimeVisionNote.value =
          source === 'inflight'
            ? '已复用最近视觉结果（并发去重）'
            : '已复用最近视觉结果（短期缓存）'
      } else {
        const total = (evt.timing && evt.timing.total_ms) || 0
        const model = (evt.timing && evt.timing.model_request_ms) || 0
        realtimeVisionNote.value = total
          ? `豆包视觉分析完成（${(total / 1000).toFixed(2)} 秒，模型 ${(model / 1000).toFixed(2)} 秒）`
          : '豆包视觉分析完成'
      }
      // 4 秒后清空，避免信息长时间停留
      setTimeout(() => {
        realtimeVisionNote.value = ''
      }, 4000)
      return
    }

    // 工具调用 arguments delta
    if (t === 'response.function_call_arguments.delta') {
      // noop（仅供调试）
      return
    }

    // 响应结束
    if (t === 'response.done' || t === 'response.completed') {
      if (isRealtimePlaying.value) {
        realtimeStatus.value = 'playing'
      } else {
        realtimeStatus.value = 'listening'
      }
      return
    }
  }

  ws.onerror = (e) => {
    console.error('Realtime WS error:', e)
    if (!realtimeIntentionalClose) {
      realtimeError.value = 'WebSocket 错误，请检查后端是否启动、Key 是否正确。'
      realtimeStatus.value = 'failed'
    }
  }

  ws.onclose = () => {
    if (realtimeHeartbeatTimer) {
      clearInterval(realtimeHeartbeatTimer)
      realtimeHeartbeatTimer = null
    }
    if (!realtimeIntentionalClose && realtimeStatus.value !== 'failed') {
      realtimeStatus.value = 'ended'
    }
  }
}

// 启动麦克风采集
const startMicCapture = async () => {
  // 1. 麦克风
  realtimeMicStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    }
  })

  // 2. AudioContext
  const Ctx = window.AudioContext || window.webkitAudioContext
  realtimeAudioContext = new Ctx()

  // 3. 加载 worklet
  await realtimeAudioContext.audioWorklet.addModule(
    new URL('./audio/pcm-worklet.js', import.meta.url).href
  )

  // 4. 创建节点
  realtimeMicSource = realtimeAudioContext.createMediaStreamSource(realtimeMicStream)
  realtimeWorkletNode = new AudioWorkletNode(realtimeAudioContext, 'pcm16k-processor')
  realtimeWorkletNode.port.onmessage = (e) => {
    // e.data 是 ArrayBuffer
    const buf = e.data
    if (realtimeWs && realtimeWs.readyState === WebSocket.OPEN && buf) {
      try {
        realtimeWs.send(buf)
      } catch (err) {
        // noop
      }
    }
  }
  realtimeMicSource.connect(realtimeWorkletNode)
  // 不需要连接到 destination（否则会回放麦克风）
}

// 停止当前播放（不结束整个会话）
const stopRealtimePlayback = () => {
  if (realtimePlayer) {
    realtimePlayer.stop()
  }
  if (realtimeWs && realtimeWs.readyState === WebSocket.OPEN) {
    try {
      realtimeWs.send(JSON.stringify({ type: 'cancel' }))
    } catch (e) {
      // noop
    }
  }
  if (realtimeStatus.value === 'playing' || realtimeStatus.value === 'answering') {
    realtimeStatus.value = 'listening'
  }
}

// 结束整个会话
const endRealtimeSession = () => {
  realtimeIntentionalClose = true

  // 1) 停止播放
  if (realtimePlayer) {
    try { realtimePlayer.stop() } catch (e) { /* noop */ }
  }
  isRealtimePlaying.value = false

  // 2) 停止麦克风
  if (realtimeMicStream) {
    try {
      realtimeMicStream.getTracks().forEach((t) => {
        try { t.stop() } catch (e) { /* noop */ }
      })
    } catch (e) {
      // noop
    }
    realtimeMicStream = null
  }
  if (realtimeWorkletNode) {
    try { realtimeWorkletNode.disconnect() } catch (e) { /* noop */ }
    realtimeWorkletNode = null
  }
  if (realtimeMicSource) {
    try { realtimeMicSource.disconnect() } catch (e) { /* noop */ }
    realtimeMicSource = null
  }
  if (realtimeAudioContext) {
    try { realtimeAudioContext.close() } catch (e) { /* noop */ }
    realtimeAudioContext = null
  }

  // 3) 心跳
  if (realtimeHeartbeatTimer) {
    clearInterval(realtimeHeartbeatTimer)
    realtimeHeartbeatTimer = null
  }

  // 4) WebSocket
  if (realtimeWs) {
    try { realtimeWs.close() } catch (e) { /* noop */ }
    realtimeWs = null
  }

  realtimeVisionNote.value = ''

  if (realtimeStatus.value !== 'failed') {
    realtimeStatus.value = 'ended'
  }
}

// ===== 生命周期 =====
onBeforeUnmount(() => {
  if (isCameraActive.value) {
    stopCamera()
  }
  // PR11: 释放当前画面 blob URL
  if (realtimeCurrentFrameUrl.value) {
    try { URL.revokeObjectURL(realtimeCurrentFrameUrl.value) } catch (e) { /* noop */ }
    realtimeCurrentFrameUrl.value = ''
  }
  if (recognition) {
    try { recognition.abort() } catch (e) { /* noop */ }
  }
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
  // PR8 清理：结束实时会话
  if (realtimeWs) {
    realtimeIntentionalClose = true
    try { realtimeWs.close() } catch (e) { /* noop */ }
    realtimeWs = null
  }
  if (realtimeMicStream) {
    try {
      realtimeMicStream.getTracks().forEach((t) => {
        try { t.stop() } catch (e) { /* noop */ }
      })
    } catch (e) { /* noop */ }
    realtimeMicStream = null
  }
  if (realtimeWorkletNode) {
    try { realtimeWorkletNode.disconnect() } catch (e) { /* noop */ }
    realtimeWorkletNode = null
  }
  if (realtimeMicSource) {
    try { realtimeMicSource.disconnect() } catch (e) { /* noop */ }
    realtimeMicSource = null
  }
  if (realtimeAudioContext) {
    try { realtimeAudioContext.close() } catch (e) { /* noop */ }
    realtimeAudioContext = null
  }
  if (realtimePlayer) {
    try { realtimePlayer.close() } catch (e) { /* noop */ }
    realtimePlayer = null
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

/* ===== PR8 实时语音视觉对话样式 ===== */
.realtime-section {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin: 1rem 0;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.realtime-hint {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.55;
  margin: 0.4rem 0 0.8rem;
}

.realtime-status-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0.6rem 0 0.8rem;
  flex-wrap: wrap;
}

.realtime-status-label {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
}

.realtime-status-pill {
  display: inline-block;
  padding: 0.25rem 0.7rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.12);
  color: #e6f1ff;
  transition: background 0.2s ease;
}

.realtime-status-connecting {
  background: rgba(255, 193, 7, 0.45);
  color: #fff;
}

.realtime-status-listening {
  background: rgba(78, 205, 196, 0.45);
  color: #fff;
}

.realtime-status-recognizing {
  background: rgba(78, 205, 196, 0.55);
  color: #fff;
}

.realtime-status-analyzing {
  background: rgba(186, 104, 200, 0.55);
  color: #fff;
}

.realtime-status-answering {
  background: rgba(116, 185, 255, 0.55);
  color: #fff;
}

.realtime-status-playing {
  background: rgba(78, 205, 196, 0.6);
  color: #fff;
}

.realtime-status-failed {
  background: rgba(244, 67, 54, 0.55);
  color: #fff;
}

.realtime-status-ended {
  background: rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.85);
}

.realtime-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin: 0.4rem 0 0.7rem;
}

.realtime-warn,
.realtime-error {
  font-size: 0.9rem;
  padding: 0.55rem 0.8rem;
  border-radius: 6px;
  margin: 0.4rem 0 0.6rem;
}

.realtime-warn {
  background: rgba(255, 193, 7, 0.18);
  border-left: 3px solid rgba(255, 193, 7, 0.8);
  color: #ffe8a1;
}

.realtime-vision-note {
  margin: 0.5rem 0;
  padding: 0.4rem 0.7rem;
  background: rgba(78, 205, 196, 0.12);
  border-left: 3px solid rgba(78, 205, 196, 0.7);
  color: #b6f3ec;
  font-size: 0.92em;
  border-radius: 4px;
}

.realtime-error {
  background: rgba(244, 67, 54, 0.18);
  border-left: 3px solid rgba(244, 67, 54, 0.85);
  color: #ffcdd2;
}

.realtime-conversation {
  margin-top: 0.8rem;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 0.75rem 1rem;
}

.realtime-frame {
  margin-bottom: 0.6rem;
}

.realtime-frame-label {
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.65);
  margin-bottom: 0.35rem;
}

.realtime-frame-image {
  max-width: 100%;
  max-height: 280px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: block;
}

.realtime-transcript,
.realtime-answer {
  margin: 0.4rem 0;
}

.realtime-transcript-label,
.realtime-answer-label {
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.65);
  margin-bottom: 0.25rem;
}

.realtime-transcript-text,
.realtime-answer-text {
  font-size: 0.98rem;
  line-height: 1.5;
  color: #fff;
  white-space: pre-wrap;
  word-break: break-word;
  min-height: 1.4em;
}

.realtime-playing-indicator {
  margin-top: 0.4rem;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: #4ecdc4;
}

.realtime-playing-dot {
  display: inline-block;
  width: 0.55rem;
  height: 0.55rem;
  background: #4ecdc4;
  border-radius: 50%;
  animation: realtime-dot-pulse 1.2s ease-in-out infinite;
}

@keyframes realtime-dot-pulse {
  0%, 100% { opacity: 0.35; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1.1); }
}

.realtime-cost-hint {
  margin-top: 0.7rem;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}

.btn-danger {
  background: rgba(244, 67, 54, 0.85);
  color: #fff;
  border: 0;
  border-radius: 6px;
  padding: 0.5rem 0.9rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;
}

.btn-danger:hover {
  background: rgba(244, 67, 54, 1);
}

.btn-danger:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
