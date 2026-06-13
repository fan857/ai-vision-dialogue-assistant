# PR4 - 摄像头截图与前端图片压缩

## 1. 功能目标

让用户可以从实时摄像头预览中**主动截取当前帧**，并在浏览器端完成**图片压缩、预览和清除**操作，为后续视觉问答接口准备好图片数据。

本次 PR 范围：

- 在摄像头预览区域增加"截取当前画面"和"清除截图"按钮。
- 使用 `<video>` + 离屏 `<canvas>` 抓取当前视频帧。
- 在浏览器端将图片压缩为 `image/jpeg`，最长边 1280px，质量 0.75。
- 页面展示压缩后的截图、原始尺寸、压缩后尺寸、文件大小、格式和截图时间。
- 正确释放 Object URL，避免内存泄漏。
- 不上传图片，不调用后端，不调用 AI。

## 2. 截图实现方式

### 2.1 触发与限制

- 按钮位置：摄像头预览区域下方新增独立的"摄像头截图与压缩"section。
- 摄像头未开启时，截图按钮**自动禁用**并显示提示"请先打开摄像头，再进行截图。"。
- 摄像头已开启但 `video.readyState < 2` 时，显示"摄像头尚未准备完成，请稍候再试。"。

### 2.2 截图流程

1. 校验摄像头状态和 video 元素 readyState。
2. 记录原始画面尺寸 `video.videoWidth` × `video.videoHeight`。
3. 计算压缩后尺寸（保持比例，最长边不超过 1280px）。
4. 离屏创建 `<canvas>`，按目标尺寸 `drawImage(video, 0, 0, targetWidth, targetHeight)`。
5. 使用 `canvas.toBlob(callback, 'image/jpeg', 0.75)` 输出 JPEG Blob。
6. 通过 `URL.createObjectURL(blob)` 生成预览 URL。
7. 写入响应式状态：`capturedImageBlob`、`capturedImagePreviewUrl`、`capturedImageMetadata`。
8. 更新状态为 `completed`，显示元数据。

### 2.3 元数据结构

```javascript
capturedImageMetadata = {
  originalWidth: 1920,
  originalHeight: 1080,
  compressedWidth: 1280,
  compressedHeight: 720,
  compressedSize: 186432, // 字节
  mimeType: 'image/jpeg',
  capturedAt: '2026/6/12 10:23:45'
}
```

## 3. Canvas 压缩逻辑

定义清晰常量，方便后续调整：

```javascript
const MAX_IMAGE_DIMENSION = 1280
const JPEG_QUALITY = 0.75
const COMPRESSED_MIME_TYPE = 'image/jpeg'
```

压缩规则：

1. 保持原始宽高比（按最长边等比缩放）。
2. 最长边超过 1280px 才缩放；原图更小则**不放大**。
3. 输出格式固定为 `image/jpeg`。
4. JPEG 压缩质量固定为 `0.75`。
5. 不保存多张历史原图，只保留当前最新截图。
6. 不上传任何视频流，只在用户主动点击时截取一帧。

## 4. Object URL 清理

为了避免内存泄漏，所有场景都正确释放 Object URL：

| 场景 | 行为 |
| --- | --- |
| 重新截图 | 先调用 `revokePreviewUrl()`，再 `URL.createObjectURL(blob)` |
| 点击"清除截图" | 调用 `revokePreviewUrl()` 清空预览 |
| Vue 组件卸载 | `onBeforeUnmount` 中调用 `revokePreviewUrl()` |
| 摄像头关闭 | 不主动清除截图，保留给用户查看或清除 |

`revokePreviewUrl()` 是统一的清理函数：

```javascript
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
```

## 5. 成本控制与隐私设计

页面在截图区域顶部明确提示用户：

> 摄像头视频不会持续上传。只有用户主动截图时，页面才会处理当前画面，并在上传前进行压缩。

本 PR 落实的成本控制策略：

- ✅ 不连续截取摄像头画面（只在用户点击时截取一帧）。
- ✅ 不上传视频流（仅在内存中处理）。
- ✅ 用户主动截图时才处理画面。
- ✅ 上传前在浏览器端压缩图片（最长边 1280px、JPEG 0.75）。
- ✅ 不保留多张历史原图，只保留当前最新截图。
- ✅ 当前仍未上传至云端（PR4 范围内不调用后端）。

## 6. 测试步骤

启动前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 `http://localhost:5173`。

### 6.1 正常截图流程

1. 点击"打开摄像头" → 浏览器弹出权限请求 → 允许 → 摄像头画面显示。
2. 点击"截取当前画面" → 状态短暂显示"正在截取并压缩画面……" → 显示截图预览。
3. 检查页面元数据：原始尺寸、压缩后尺寸（最长边 ≤ 1280px）、文件大小、格式、时间。
4. 多次点击"截取当前画面" → 旧截图被新截图替换，DevTools 内存中不应持续增长。

### 6.2 异常与边界

1. 摄像头未开启时，"截取当前画面"按钮应处于禁用状态，下方有"请先打开摄像头，再进行截图。"提示。
2. 点击"清除截图" → 预览、元数据、状态全部清空，摄像头保持打开。
3. 关闭摄像头 → 已有的截图**不会被强制清除**（除非用户主动清除）。
4. 截图失败时（如浏览器不支持 canvas toBlob）→ 显示明确错误，不崩溃。

### 6.3 原有功能回归

- ✅ 摄像头打开/关闭、实时预览正常。
- ✅ 麦克风语音识别（PR3）正常。
- ✅ 手动输入问题文本（PR3 fallback）正常。
- ✅ 浏览器控制台无明显错误。

### 6.4 构建验证

```bash
cd frontend
npm run build
```

构建必须成功。

## 7. 当前限制

- 图片**仅保存在浏览器内存中**，刷新页面后丢失。
- 截图只在用户主动点击时进行，**不会自动截图**。
- 图片**未上传到任何后端**，暂未对接 FastAPI。
- 尚未对接多模态模型，仅作为视觉问答的数据准备。

## 8. 后续将如何连接视觉问答接口

后续 PR（预计 PR5/PR6）将：

1. 新增 FastAPI 接口 `POST /api/vision/ask`，接收 `multipart/form-data`：
   - `image`：`capturedImageBlob`（JPEG 压缩后）
   - `question`：用户问题文本（来自 `userQuestionText`）
2. 前端使用 `fetch` + `FormData` 上传图片 Blob，**不直接上传视频流**。
3. 后端调用多模态模型理解画面 + 回答问题，**只在用户提问时调用**，实现按需调用模型的成本控制策略。
4. 返回结构化结果后，前端展示文本回答，并在后续 PR 中接入 TTS 朗读。

## 9. 状态命名

| 状态变量 | 类型 | 含义 |
| --- | --- | --- |
| `captureStatus` | `'idle' \| 'capturing' \| 'completed' \| 'failed'` | 截图处理状态 |
| `captureError` | `string` | 截图错误提示 |
| `capturedImageBlob` | `Blob \| null` | 压缩后的图片 Blob，供后续上传 |
| `capturedImagePreviewUrl` | `string` | 预览用的 Object URL |
| `capturedImageMetadata` | `object \| null` | 截图元数据 |
