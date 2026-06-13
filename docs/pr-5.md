# PR5 - 前后端视觉对话请求链路

## 1. 功能目标

打通"前端提交压缩后的截图 + 用户问题 → FastAPI 后端接收并校验 → 返回请求接收结果"的完整链路。

本次 PR 范围：

- 前端使用 `FormData` 提交 `question`（用户问题文本）和 `image`（压缩后的 JPEG Blob）到后端。
- 后端 `POST /api/vision-dialogue` 接口接收请求并完成参数校验。
- 后端计算图片 SHA-256、生成 UUID `request_id`、返回请求接收结果。
- 前端展示后端结果（message、request_id、图片格式、图片大小、SHA-256 前缀）。
- 前端 Vite dev server 增加 `/api` 代理，指向 FastAPI 后端 `http://localhost:3001`。

**本次不接入任何真实多模态 AI 模型，不返回伪造的视觉识别答案。**

## 2. 请求格式

### 2.1 端点

```
POST /api/vision-dialogue
Content-Type: multipart/form-data
```

### 2.2 请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `question` | `string` | 是 | 用户问题文本，去除首尾空格后非空，最长 1000 字符 |
| `image` | `file` | 是 | 压缩后的 JPEG / PNG / WebP 图片，文件名默认为 `snapshot.jpg` |

### 2.3 成功响应（HTTP 200）

```json
{
  "status": "accepted",
  "message": "视觉对话请求已接收，当前尚未接入 AI 模型",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "你看到了什么",
  "image": {
    "filename": "snapshot.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 186432,
    "sha256": "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca7"
  }
}
```

### 2.4 错误响应

| HTTP 状态码 | 触发条件 | 错误信息（`detail`） |
| --- | --- | --- |
| 400 | 问题为空 / 超过 1000 字符 | `问题不能为空` / `问题长度超过限制（最大 1000 字符）` |
| 400 | 图片格式不支持 | `仅支持 JPEG、PNG 或 WebP 图片` |
| 400 | 图片为空 | `图片内容为空` |
| 413 | 图片大小超过 2 MB | `图片大小超过限制（最大 2 MB）` |

## 3. 后端校验规则

### 3.1 问题校验

```python
question_clean = (question or "").strip()
if not question_clean:
    raise HTTPException(400, "问题不能为空")
if len(question_clean) > MAX_QUESTION_LENGTH:
    raise HTTPException(400, f"问题长度超过限制（最大 {MAX_QUESTION_LENGTH} 字符）")
```

### 3.2 图片格式校验

```python
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
```

其他格式直接返回 400 `仅支持 JPEG、PNG 或 WebP 图片`。

### 3.3 图片大小校验

```python
MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
```

- 空图片 → 400 `图片内容为空`
- 超过 2 MB → 413 `图片大小超过限制（最大 2 MB）`

### 3.4 SHA-256 计算

```python
sha256 = hashlib.sha256(image_bytes).hexdigest()
```

为后续缓存命中、重复请求去重保留必要的信息基础（PR5 不使用，仅做计算）。

## 4. 图片处理方式（隐私保护）

后端对图片的处理**全程在内存中**：

- ✅ 只通过 `await image.read()` 读取到内存
- ✅ 立即计算 SHA-256 后即返回
- ❌ 不写入磁盘
- ❌ 不上传到七牛云
- ❌ 不写入数据库
- ❌ 不在日志中输出图片二进制或 Base64
- ❌ 不返回图片原始内容或 Base64
- ❌ 不调用任何 AI 模型

## 5. 前端提交逻辑

### 5.1 Vite 代理配置

`frontend/vite.config.js` 增加：

```javascript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:3001',
      changeOrigin: true
    }
  }
}
```

这样前端可以直接使用相对路径 `/api/vision-dialogue`，开发期间由 Vite 代理转发到后端。

### 5.2 提交条件

- ✅ `capturedImageBlob` 存在
- ✅ `userQuestionText.trim()` 非空
- ✅ 当前没有正在进行的提交

不满足条件时：

- 没有截图 → "请先打开摄像头并截取当前画面。"
- 没有问题 → "请先通过语音识别或手动输入问题。"

### 5.3 提交实现

```javascript
const formData = new FormData()
formData.append('question', questionClean)
formData.append('image', capturedImageBlob.value, 'snapshot.jpg')

const response = await fetch('/api/vision-dialogue', {
  method: 'POST',
  body: formData
})
```

### 5.4 防重复提交

- 提交期间 `dialogueStatus = 'submitting'`
- 提交按钮 `disabled` 防止重复点击
- 错误时不清空 `capturedImageBlob` 和 `userQuestionText`，用户可重试

### 5.5 错误处理

- 优先展示后端 `detail` 字段
- 网络错误（fetch 抛 TypeError）→ "网络异常，无法连接后端服务。请确认后端已启动（http://localhost:3001）。"
- 其他错误 → 展示原始错误信息

### 5.6 结果展示

提交成功后，页面展示：

- 后端 `message`
- `request_id`（UUID）
- 图片格式（`content_type`）
- 图片大小（KB / MB 易读格式）
- SHA-256 前 16 位（避免页面过长）
- 顶部黄色提示："请求链路验证成功，当前尚未接入 AI 视觉模型。"

## 6. 状态命名

| 状态变量 | 类型 | 含义 |
| --- | --- | --- |
| `dialogueStatus` | `'idle' \| 'submitting' \| 'success' \| 'failed'` | 提交状态 |
| `dialogueError` | `string` | 错误提示 |
| `dialogueResult` | `object \| null` | 后端返回数据 |

## 7. 成本控制与隐私设计

本 PR 继续落实成本控制和隐私策略：

- ✅ 不上传连续视频流（仍然只在用户主动点击截图时处理一帧）
- ✅ 只上传用户主动截取的单张图片
- ✅ 图片上传前已经在浏览器端压缩（PR4 的成果）
- ✅ 后端限制最大 2 MB
- ✅ 图片不落盘、不持久化
- ✅ 当前不调用模型，因此不会产生模型费用
- ✅ SHA-256 为后续缓存和去重做准备
- ✅ 页面明确提示："图片仅在用户主动提交时发送到后端。当前后端只进行参数校验，不保存图片，也不会调用 AI 模型。"

## 8. 测试步骤

### 8.1 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 3001
```

验证：

- `http://localhost:3001/api/health` → `{"status":"ok",...}`
- `http://localhost:3001/docs` → Swagger UI 应能看到 `POST /api/vision-dialogue`

### 8.2 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

### 8.3 功能验证清单

| # | 测试项 | 预期 |
| --- | --- | --- |
| 1 | 原有摄像头、语音识别、截图功能 | 全部正常 |
| 2 | 无截图时点击"提交视觉问题" | 按钮被禁用（`disabled`），不可点击 |
| 3 | 有截图、无问题时提交 | "请先通过语音识别或手动输入问题。" |
| 4 | 有问题、无截图时提交 | "请先打开摄像头并截取当前画面。" |
| 5 | 有截图、有问题，正常提交 | 状态显示"请求已成功提交"，展示 request_id、图片格式、大小、SHA-256 前缀 |
| 6 | 顶部黄色提示 | "请求链路验证成功，当前尚未接入 AI 视觉模型。" |
| 7 | 提交期间点击提交按钮 | 按钮被禁用，无法重复点击 |
| 8 | 关闭后端后提交 | 友好提示"网络异常，无法连接后端服务。" |
| 9 | 后端目录检查 | 没有生成任何图片文件（不落盘） |
| 10 | DevTools Network | 请求路径为 `/api/vision-dialogue`，方法为 `POST` |
| 11 | 浏览器 / 后端控制台 | 无明显错误 |
| 12 | 提交后问题、截图仍保留 | 用户可调整后再次提交 |

### 8.4 后端边界测试（可选）

```bash
# 问题为空
curl -X POST http://localhost:3001/api/vision-dialogue \
  -F "question=" \
  -F "image=@some.jpg"
# → {"detail":"问题不能为空"}

# 图片格式错误
curl -X POST http://localhost:3001/api/vision-dialogue \
  -F "question=hello" \
  -F "image=@some.gif;type=image/gif"
# → {"detail":"仅支持 JPEG、PNG 或 WebP 图片"}
```

### 8.5 构建验证

```bash
cd frontend
npm run build
```

### 8.6 后端语法检查

```bash
cd d:\2026qiniu2
python -m compileall backend
```

## 9. 当前限制

- 后端**不调用任何 AI 模型**，不会产生模型费用。
- 图片**不保存**，刷新页面后丢失。
- **不支持多轮对话**，每次提交都是独立请求。
- **不接入七牛云**图片上传。
- SHA-256 计算了但**暂未用于缓存或去重**。
- **没有 WebSocket / 流式响应**。

## 10. 后续 PR

### PR6 - 接入多模态 AI 模型

- 后端调用多牛云多模态大模型（或七牛云 AI 服务）：
  - 输入：图片（bytes）+ 问题文本
  - 输出：模型生成的文本回答
- 返回结构增加 `answer` 字段（AI 生成的回复）
- 引入"按需调用"成本控制：
  - 只有在用户主动提交时才调用模型
  - 简单问题不调用视觉模型
  - 多轮对话复用最近一次视觉摘要

### PR7 - 语音合成朗读

- 将 AI 文本回答转成语音
- 浏览器端 TTS 播放

## 11. 关键文件

| 文件 | 状态 |
| --- | --- |
| `backend/main.py` | 新增 `POST /api/vision-dialogue` 接口 |
| `backend/requirements.txt` | 已包含 `python-multipart` |
| `frontend/vite.config.js` | 新增 `/api` 代理 |
| `frontend/src/App.vue` | 新增提交按钮、提交逻辑、结果展示 |
| `README.md` | 标记 PR5 完成 |
| `docs/pr-5.md` | 新建本文档 |
