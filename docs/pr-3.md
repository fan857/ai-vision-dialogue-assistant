# PR3：麦克风语音识别功能

## 功能概述

实现浏览器端中文语音识别。用户点击"开始语音识别"按钮后，浏览器调用 Web Speech API，将识别到的中文文本实时显示在页面中；用户也可以点击"停止识别"提前结束识别。提供手动输入框作为 fallback，保证在浏览器不支持语音识别时仍然可以输入问题文本。

本 PR 只做前端语音识别，不涉及音频上传、不调用 AI 模型、不生成 AI 回复。

## 实现细节

1. 在 `App.vue` 中新增"麦克风语音识别"区域，与摄像头预览区域并列展示。
2. 通过 `window.SpeechRecognition || window.webkitSpeechRecognition` 探测浏览器能力。
3. 设置识别语言为 `zh-CN`，开启 `interimResults` 实现"准实时"显示。
4. 使用响应式变量管理状态：
   - `speechStatus`：`idle | requesting | recognizing | completed | failed | unsupported`
   - `speechError`：识别失败时的错误信息
   - `userQuestionText`：识别结果（与手动输入框共用，方便后续 PR4 截图上传和视觉问答）
5. 监听 `onstart` / `onresult` / `onerror` / `onend` 事件，更新状态与文本。
6. 对常见错误（`not-allowed`、`no-speech`、`audio-capture`、`network` 等）做中文友好提示。
7. 浏览器不支持时显示提示，并允许用户继续使用手动输入框。
8. 组件卸载时调用 `recognition.abort()` 释放资源。

## 技术实现

### 前端（Vue3）

- Web Speech API：`SpeechRecognition` / `webkitSpeechRecognition`
- 语音识别语言：`zh-CN`
- 响应式状态：`ref` / `computed`
- 状态机：未开始 → 请求中 → 识别中 → 完成 / 失败
- 错误处理：浏览器不支持、权限拒绝、无语音、设备不可用、网络错误

### 状态变量

| 变量 | 说明 |
| --- | --- |
| `speechStatus` | 语音识别当前状态 |
| `speechError` | 当前错误信息（无错误时为空字符串） |
| `userQuestionText` | 识别结果 / 手动输入的问题文本（共用） |
| `SpeechRecognitionCtor` | 浏览器提供的构造器（可能为 null） |
| `recognition` | 当前 SpeechRecognition 实例（用于停止 / 卸载） |

## 测试方式

### 1. 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 `http://localhost:5173`。

> 注意：Web Speech API 在 `http://localhost` 下通常可用；线上必须使用 HTTPS 才能调用。

### 2. 功能测试

1. 页面打开后，可以正常打开/关闭摄像头（PR2 功能不受影响）。
2. 点击"开始语音识别"按钮，浏览器弹出麦克风权限请求，点击"允许"。
3. 状态依次变为：未开始 → 请求中 → 识别中 → 识别完成。
4. 对着麦克风说一句中文，例如"你看到了什么"，页面会实时显示识别文本。
5. 点击"停止识别"按钮，识别立刻结束。
6. 在"手动输入（fallback）"中输入问题，文本会与识别结果共用同一个状态。
7. 刷新页面，识别结果会清空。

### 3. 异常测试

- 拒绝麦克风权限：状态变为"识别失败"，并显示"麦克风权限被拒绝"提示。
- 不说话等待自动结束：状态变为"识别完成"，文本为空。
- 使用 Firefox / Safari 等不支持 Web Speech API 的浏览器：状态显示"浏览器不支持 Web Speech API"，按钮被禁用，但仍可使用手动输入框。
- 关闭网络再开始识别：状态变为"识别失败"，显示"网络错误"提示。

### 4. 构建验证

```bash
cd frontend
npm run build
```

构建应能成功，无报错。

## 限制

- 本 PR 仅做前端语音识别，不向后端发送任何音频或文本。
- 没有调用任何 AI 模型，不生成回复。
- 没有做音频录制与音频文件上传。
- Web Speech API 的中文识别准确度依赖浏览器内置服务（Chrome / Edge 使用 Google 在线服务），断网情况下可能失败。
- Firefox、Safari 桌面版等浏览器不支持 Web Speech API，需要通过手动输入框 fallback。
- 由于浏览器安全策略，线上环境必须使用 HTTPS 才能调用 Web Speech API。

## 后续

- PR4：在用户提问时截取当前摄像头画面 + 用户文本（来自 `userQuestionText`）上传到后端，调用多模态模型生成回复。
- PR5：将 AI 回复通过浏览器语音合成朗读出来。
- PR6：按需进行节流、压缩与多轮摘要复用，降低调用成本。

## 相关文件

- `frontend/src/App.vue`：主页面组件，新增语音识别 UI 与逻辑
- `README.md`：更新"当前完成内容"与"项目结构"
- `docs/pr-3.md`：本 PR 文档
