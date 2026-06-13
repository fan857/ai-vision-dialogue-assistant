# PR7：AI 回答语音合成与朗读

## 1. PR7 功能目标

本 PR 完成 MVP 链路中的最后一步——**AI 回答语音朗读**：

> Doubao-Seed-2.0-Pro 视觉模型返回真实回答后，前端使用浏览器原生 `window.speechSynthesis`
> 将 AI 回答朗读出来，使用户在不便阅读屏幕时也能听到 AI 的回复。

本 PR **不**接入任何第三方云端 TTS 服务，**不**需要新增 API Key，**不**产生额外费用。

## 2. SpeechSynthesis API 实现方式

使用浏览器内置 Web Speech API：

```js
const u = new SpeechSynthesisUtterance(text)
u.lang = 'zh-CN'
u.rate = 1
u.pitch = 1
u.volume = 1
window.speechSynthesis.speak(u)
```

事件回调：

| 事件 | 用途 |
| --- | --- |
| `onstart` | 设置 `isSpeaking = true`、`ttsStatus = 'speaking'` |
| `onend` | 正常播放完成时设置 `ttsStatus = 'done'`；被 cancel 时保留 `stopped` |
| `onerror` | 区分 `canceled` / `interrupted`（用户主动停止）和其他错误 |

## 3. 中文语音选择逻辑

```js
const pickZhVoice = (voices) => {
  if (!voices || voices.length === 0) return null
  const zhCn = voices.find(v => (v.lang || '').toLowerCase() === 'zh-cn')
  if (zhCn) return zhCn
  const zhAny = voices.find(v => (v.lang || '').toLowerCase().startsWith('zh'))
  if (zhAny) return zhAny
  return null // 让浏览器选择默认 voice
}
```

优先级：

1. `lang === 'zh-CN'`（普通话）
2. 其他中文（`zh-TW` / `zh-HK` 等）
3. 浏览器默认 voice（兜底，不会因为没找到中文 voice 而报错）

兼容性处理：

- 部分浏览器首次 `getVoices()` 返回空数组
- 已注册 `onvoiceschanged` 监听，voice 列表就绪时自动重新选择
- 在 `onBeforeUnmount` 中清理监听，避免内存泄漏

## 4. 自动朗读 / 手动朗读

- 提供 `autoSpeakEnabled` 复选框（默认开启）
- 提交 `/api/vision-dialogue` 成功后，若 `autoSpeakEnabled === true`，自动朗读 `data.answer`
- 关闭自动朗读时，仅显示文字回答，不自动播放
- 朗读控件区提供「朗读回答」「停止朗读」按钮，用户可随时手动触发
- 错误 / 空回答 / 旧回答不会被朗读
- 新请求开始前调用 `speechSynthesis.cancel()` 停止旧朗读，避免多个回答同时播放

## 5. 浏览器兼容与提示

| 场景 | 处理 |
| --- | --- |
| 不存在 `window.speechSynthesis` | 显示「当前浏览器不支持语音合成，请使用最新版 Chrome 或 Edge」，朗读按钮禁用 |
| 朗读失败（onerror） | 显示 `ttsError`，不影响文字回答，不影响截图和问题，允许重新提交 |
| 浏览器自动播放策略拦截 | 朗读按钮仍可手动点击播放（用户手势） |
| 切换 voice 抛出异常 | 捕获并忽略，回退到默认 voice |

## 6. 生命周期清理

`onBeforeUnmount` 中：

```js
if (speechSynthesisSupported.value) {
  window.speechSynthesis.cancel()          // 停止朗读
  window.speechSynthesis.onvoiceschanged = null  // 移除 voice 监听
}
```

防止：

- 组件卸载后还在朗读（用户体验问题）
- voice 监听器重复注册（内存泄漏）

## 7. 成本与隐私

| 项 | 说明 |
| --- | --- |
| 是否调用云端 TTS | ❌ 不调用 |
| 是否需要新 API Key | ❌ 不需要 |
| 是否上传 AI 回答 | ❌ 仅在浏览器内朗读 |
| 是否自动重复朗读 | ❌ 仅在新回答生成时或用户主动点击时 |
| 朗读频率 | 每次点击 / 每次新回答 = 一次 |
| 是否产生额外费用 | ❌ 无 |

页面提示：

> AI 回答使用浏览器原生语音合成功能朗读，不调用额外云端语音服务，不产生额外语音 API 费用。

## 8. 测试步骤

启动后端和前端（README 中的启动命令）后：

1. 打开 `http://localhost:5173`
2. 打开摄像头 → 截取画面 → 输入问题 → 提交视觉问题
3. AI 回答出现后，**应自动开始朗读**（默认开启）
4. 页面下方「语音状态」徽标应从 `未朗读` → `正在朗读` → `已完成`
5. 再次提交新的视觉问题，旧朗读应立即停止，新回答被朗读
6. 取消勾选「自动朗读 AI 回答」，新回答不再自动播放
7. 点击「朗读回答」可手动重新朗读
8. 点击「停止朗读」应立即停止
9. 关闭浏览器标签页后，不应再听到声音
10. 使用不支持 SpeechSynthesis 的浏览器，应看到提示而不报错

## 9. 当前限制

- 不同系统（Windows / macOS / Linux / Android / iOS）内置中文音色差异较大，质量受浏览器 / 系统限制
- 部分浏览器在 `<10s` 短文本上可能不发出声音
- 没有音频文件生成或下载接口
- 没有自定义音色 / 语速持久化（每次刷新页面回到默认 `rate=1, pitch=1, volume=1`）
- 没有多轮对话 / 上下文记忆（每次只朗读最新回答）

## 10. 本次未实现

- 云端 TTS（火山语音 / 第三方）
- 音频文件下载
- 语音克隆 / 自定义音色训练
- 多轮对话 / 上下文记忆
- 朗读历史
- 朗读速度 / 音调持久化

这些功能在 MVP 链路之外，留待后续 PR 或不实现。
