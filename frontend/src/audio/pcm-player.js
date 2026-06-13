// 流式 PCM 播放器：接收 24kHz 16bit 单声道 PCM 分片，按顺序排队播放
// - 复用单一 AudioContext
// - 使用 queue + current 控制
// - 避免音频重叠
// - 支持 stop() 立即停止

export class PCMStreamPlayer {
  constructor() {
    this.audioContext = null
    this.queue = [] // 等待播放的 AudioBuffer
    this.current = null // 当前正在播放的 source
    this.playing = false
    this.onStateChange = null
    this._onended = null
  }

  _setState(s) {
    this.playing = s
    if (typeof this.onStateChange === 'function') {
      try {
        this.onStateChange(s)
      } catch (e) {
        // noop
      }
    }
  }

  async _ensureContext() {
    if (!this.audioContext) {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) {
        throw new Error('浏览器不支持 Web Audio API')
      }
      this.audioContext = new Ctx({ sampleRate: 24000 })
    }
    if (this.audioContext.state === 'suspended') {
      try {
        await this.audioContext.resume()
      } catch (e) {
        // noop
      }
    }
    return this.audioContext
  }

  /**
   * 推送一段 24kHz 16bit 单声道 PCM 字节
   */
  async push(pcmBytes) {
    if (!pcmBytes || pcmBytes.byteLength === 0) return
    const ctx = await this._ensureContext()
    // 转换 Int16 -> Float32
    const int16 = new Int16Array(pcmBytes.buffer, pcmBytes.byteOffset, pcmBytes.byteLength / 2)
    const float32 = new Float32Array(int16.length)
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / (int16[i] < 0 ? 0x8000 : 0x7fff)
    }
    const buffer = ctx.createBuffer(1, float32.length, 24000)
    buffer.copyToChannel(float32, 0)
    this.queue.push(buffer)
    this._scheduleNext()
  }

  _scheduleNext() {
    if (this.current) return // 已有正在播放
    if (this.queue.length === 0) {
      this._setState(false)
      return
    }
    const ctx = this.audioContext
    const buffer = this.queue.shift()
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    source.onended = () => {
      this.current = null
      if (typeof this._onended === 'function') {
        try { this._onended() } catch (e) { /* noop */ }
      }
      this._scheduleNext()
    }
    this.current = source
    this._setState(true)
    try {
      source.start(0)
    } catch (e) {
      // 已经在播放或 context 关闭
      this.current = null
      this._scheduleNext()
    }
  }

  /**
   * 立即停止播放并清空队列
   */
  stop() {
    this.queue = []
    if (this.current) {
      try {
        this.current.onended = null
        this.current.stop()
      } catch (e) {
        // noop
      }
      this.current = null
    }
    this._setState(false)
  }

  /**
   * 完整关闭（一般组件卸载时调用）
   */
  async close() {
    this.stop()
    if (this.audioContext) {
      try {
        await this.audioContext.close()
      } catch (e) {
        // noop
      }
      this.audioContext = null
    }
  }
}
