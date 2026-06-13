// AudioWorklet processor：把浏览器麦克风输入转换为 16kHz 16bit 单声道 PCM
// 通过 port.postMessage 发送 Int16Array buffer 到主线程
//
// 关键点：
// - 浏览器 getUserMedia 默认给出 44.1kHz 或 48kHz 采样率
// - 通过简单的线性重采样降到 16kHz
// - 转换为 Float32 -> Int16 PCM
// - 每 100ms 发送一个分片（1600 samples @ 16kHz）

class PCM16kProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    // 浏览器原生采样率（由 AudioContext 决定）
    this.sourceSampleRate = sampleRate
    this.targetSampleRate = 16000
    this.chunkSize = 1600 // 100ms at 16kHz
    this.buffer = new Float32Array(this.chunkSize)
    this.bufferPos = 0
    this.enabled = true
    this.port.onmessage = (e) => {
      if (e.data && e.data.type === 'stop') {
        this.enabled = false
      }
    }
  }

  process(inputs) {
    if (!this.enabled) return false
    const input = inputs[0]
    if (!input || input.length === 0) return true
    const channel = input[0]
    if (!channel || channel.length === 0) return true

    // 线性重采样到 16kHz
    const ratio = this.sourceSampleRate / this.targetSampleRate
    const outLen = Math.floor(channel.length / ratio)
    for (let i = 0; i < outLen; i++) {
      const srcIdx = i * ratio
      const idx0 = Math.floor(srcIdx)
      const idx1 = Math.min(idx0 + 1, channel.length - 1)
      const frac = srcIdx - idx0
      const sample = channel[idx0] * (1 - frac) + channel[idx1] * frac
      this.buffer[this.bufferPos++] = sample
      if (this.bufferPos >= this.chunkSize) {
        this._flush()
      }
    }
    return true
  }

  _flush() {
    // Float32 -> Int16
    const int16 = new Int16Array(this.chunkSize)
    for (let i = 0; i < this.chunkSize; i++) {
      const s = Math.max(-1, Math.min(1, this.buffer[i]))
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    // 复制到独立 buffer 后转移（避免[neutered]问题）
    const buf = int16.buffer.slice(0)
    this.port.postMessage(buf, [buf])
    this.bufferPos = 0
  }
}

registerProcessor('pcm16k-processor', PCM16kProcessor)
