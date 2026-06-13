# PR6 - 接入火山方舟 Coding Plan Doubao-Seed-2.0-Pro 视觉模型

## 1. 功能目标

打通"前端提交压缩后的截图 + 用户问题 → 后端调用真实视觉模型 → 返回真实 AI 回答"的完整链路。

本次 PR 范围：

- 后端调用**真实的**火山方舟 Coding Plan Doubao-Seed-2.0-Pro 视觉模型。
- 严格固定 Base URL 为 `https://ark.cn-beijing.volces.com/api/coding/v3`，**禁止切换到 `/api/v3`**，避免产生 Coding Plan 之外的费用。
- 使用 `httpx.AsyncClient` 异步调用，不使用 OpenAI SDK。
- API Key、Authorization 头、图片 Base64 **不写入日志**。
- 前端展示真实 AI 回答、模型名、request_id、Token 使用量。
- 一键请求只产生一次模型调用，**不自动重试、不使用流式响应**。

**禁止使用模拟回答、禁止伪造 AI 结果。**

## 2. 固定模型配置

| 项 | 值 |
| --- | --- |
| 模型 | `doubao-seed-2.0-pro` |
| Base URL | `https://ark.cn-beijing.volces.com/api/coding/v3` |
| 端点 | `POST /chat/completions` |
| 完整 URL | `https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions` |
| 鉴权 | `Authorization: Bearer <ARK_API_KEY>` |
| 默认超时 | 60 秒 |
| 最大输出 token | 300 |

⚠️ **禁止**自动切换到 `https://ark.cn-beijing.volces.com/api/v3`（会产生 Coding Plan 之外的按量计费费用）。  
⚠️ **不使用** OpenAI API Key 或 OpenAI 官方服务。

## 3. 环境变量

`backend/.env.example` 模板：

```env
# Coding Plan 固定端点
ARK_API_BASE=https://ark.cn-beijing.volces.com/api/coding/v3

# 火山方舟 Coding Plan API Key
ARK_API_KEY=your_coding_plan_api_key_here

# 视觉模型名
ARK_MODEL=doubao-seed-2.0-pro

# 单次请求超时时间（秒）
ARK_TIMEOUT_SECONDS=60

# 模型最大输出 token 数（成本控制）
ARK_MAX_TOKENS=300
```

真实配置放在 `backend/.env`（已在 `.gitignore` 中，**不会提交**）。

## 4. 依赖更新

`backend/requirements.txt` 新增：

```
httpx==0.27.0
python-dotenv==1.0.1
```

> 明确**不使用** OpenAI SDK，避免依赖膨胀和潜在的 Base URL 误用。

## 5. 后端实现

### 5.1 目录结构

```
backend/
├── main.py                 # 路由 + 校验 + 调用 vision_model
├── requirements.txt
├── .env.example
└── services/
    ├── __init__.py
    └── vision_model.py     # Coding Plan 客户端
```

### 5.2 `services/vision_model.py` 职责

1. 通过 `python-dotenv` 加载 `backend/.env`。
2. 读取环境变量：`ARK_API_KEY` / `ARK_API_BASE` / `ARK_MODEL` / `ARK_TIMEOUT_SECONDS` / `ARK_MAX_TOKENS`。
3. **安全检查**：仅当 `ARK_API_BASE` 包含 `/api/coding/v3` 时才继续调用，否则抛出 `config_error`。
4. 将图片字节编码为 `data:<content_type>;base64,<...>` 的 Data URL。
5. 构造 OpenAI 兼容格式的多模态请求（system + user with image_url + text）。
6. 使用 `httpx.AsyncClient` 异步调用 `POST /chat/completions`。
7. 提取 `choices[0].message.content` 作为模型回答。
8. 提取 `usage`（仅在上游返回时使用，否则返回 `None`）。
9. 错误处理：区分鉴权失败、Coding Plan 无权限、模型名错误、不支持图片、超时、限流、上游 5xx、响应结构异常、回答为空等。

### 5.3 `main.py` 行为

- 保留 PR5 全部校验：问题非空 / ≤ 1000 字；图片格式 JPEG/PNG/WebP；图片 ≤ 2 MB；图片非空。
- 计算图片 SHA-256。
- 校验通过后调用 `call_vision_model()`，捕获 `VisionModelError` 并以 `HTTPException` 抛出对应状态码和友好 `detail`。
- 成功时返回：

```json
{
  "status": "success",
  "message": "AI 已完成视觉分析",
  "request_id": "UUID",
  "answer": "模型真实回答（原文）",
  "model": "doubao-seed-2.0-pro",
  "question": "用户问题",
  "image": {
    "content_type": "image/jpeg",
    "size_bytes": 76595,
    "sha256": "图片 SHA-256"
  },
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

`usage` 来自上游真实返回；上游未返回时设为 `null`，**不伪造**。

### 5.4 日志规范

后端日志**只**记录：

- `request_id`（UUID）
- 状态码
- 错误类型（`auth_error` / `not_found` / `timeout` / `rate_limited` / `upstream_error` / `empty_answer` 等）
- 截断的响应体前缀（最多 200 字符，且**不**包含图片 Base64）

日志**不**记录：

- ❌ API Key
- ❌ Authorization 头
- ❌ 完整请求体
- ❌ 图片 Base64
- ❌ 完整上游响应 JSON

## 6. 请求与响应示例

### 6.1 Coding Plan 请求（脱敏）

```http
POST https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions
Authorization: Bearer <ARK_API_KEY>
Content-Type: application/json

{
  "model": "doubao-seed-2.0-pro",
  "messages": [
    {
      "role": "system",
      "content": "你是可靠的 AI 视觉对话助手。请根据图片和用户问题回答。只描述能够确认的内容，不确定时明确说明，不要编造。"
    },
    {
      "role": "user",
      "content": [
        { "type": "image_url", "image_url": { "url": "data:image/jpeg;base64,<...>" } },
        { "type": "text", "text": "你看到了什么？" }
      ]
    }
  ],
  "max_tokens": 300
}
```

### 6.2 成功响应（脱敏示例）

```json
{
  "status": "success",
  "message": "AI 已完成视觉分析",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "图片中是一台放在桌面上的笔记本电脑，屏幕显示着代码编辑器。",
  "model": "doubao-seed-2.0-pro",
  "question": "你看到了什么？",
  "image": {
    "content_type": "image/jpeg",
    "size_bytes": 76595,
    "sha256": "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca7"
  },
  "usage": {
    "prompt_tokens": 842,
    "completion_tokens": 56,
    "total_tokens": 898
  }
}
```

## 7. 错误处理矩阵

| 触发条件 | HTTP | 错误信息（`detail`） |
| --- | --- | --- |
| `ARK_API_KEY` 缺失 | 500 | 后端未配置 ARK_API_KEY，无法调用视觉模型。 |
| `ARK_API_BASE` 不含 `/api/coding/v3` | 500 | 当前 PR6 只允许使用 Coding Plan 端点（必须包含 /api/coding/v3），已拒绝继续调用。 |
| 上游 401/403 | 401 | 视觉模型鉴权失败，请检查 ARK_API_KEY 或 Coding Plan 权限。 |
| 上游 404 | 404 | 视觉模型端点或模型名称未找到。 |
| 上游 408 / `TimeoutException` | 504 | 视觉模型请求超时，请稍后重试。 |
| 上游 429 | 429 | 视觉模型请求被限流，请稍后重试。 |
| 上游 5xx | 502 | 视觉模型服务暂时不可用，请稍后重试。 |
| 响应 body 含 "image ... not support" | 400 | 当前模型不支持图片输入。 |
| 响应 body 含 "model not exist / invalid" | 404 | 模型名称不被识别。 |
| 响应 body 含 "coding plan / subscribe" | 401 | 当前账号没有 Coding Plan 订阅。 |
| `choices` 缺失 / 空 / 回答为空 | 502 | 视觉模型返回了空内容，请更换问题或截图后重试。 |
| 响应非 JSON | 502 | 视觉模型返回了非 JSON 数据。 |

前端展示后端 `detail` 字段；网络异常（fetch 失败）则展示"网络异常，无法连接后端服务"。

## 8. 前端修改

### 8.1 提交流程

- 保留 PR5 的 `FormData` 提交方式，地址 `/api/vision-dialogue`。
- 提交中按钮禁用，提示："**AI 正在分析当前画面……**"。
- 成功后顶部提示："**AI 已完成视觉分析**"。
- 失败时保留截图和问题，可重试。

### 8.2 结果展示

- **AI 视觉回答**（真实模型输出，绿色框）
- **模型**：`doubao-seed-2.0-pro`
- **request_id**（UUID）
- **图片大小**（KB / MB）
- **Token 使用**：提示 token / 完成 token / 合计 token（仅在上游真实返回时显示）

页面顶部隐私提示更新为：

> 图片仅在用户主动提交时发送到后端。后端会调用火山方舟 Coding Plan Doubao-Seed-2.0-Pro 视觉模型，并将真实回答返回。

## 9. 成本控制与隐私设计

| 设计 | 说明 |
| --- | --- |
| 不上传视频流 | 仍然只在用户主动点击截图时处理一帧 |
| 只上传压缩图片 | PR4 的 1280px / JPEG 0.75 |
| 后端限制 2 MB | PR5 校验 |
| 固定 Coding Plan 端点 | `vision_model.py` 中硬性检查 `/api/coding/v3` |
| 不自动重试 | 单次请求失败由用户决定是否重试 |
| 不使用流式 | 减少连接占用 |
| 不记录 Key / 头 / Base64 | 日志规范只记录 request_id、状态码、错误类型 |
| 输出 ≤ 300 tokens | 控制单次成本 |
| 用户点击一次只调用一次 | 提交期间按钮 `disabled` 防重入 |

## 10. 测试步骤

### 10.1 启动后端

```bash
cd backend
cp .env.example .env
# 编辑 .env，将 ARK_API_KEY 替换为真实 Coding Plan Key
pip install -r requirements.txt
uvicorn main:app --reload --port 3001
```

### 10.2 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 10.3 功能验证

| # | 测试项 | 预期 |
| --- | --- | --- |
| 1 | `GET /api/health` | `{"status":"ok",...}` |
| 2 | Swagger `POST /api/vision-dialogue` 可见 | ✅ |
| 3 | 原有摄像头、语音、截图功能 | 全部正常 |
| 4 | 提交视觉问题 → 成功 | 展示"AI 已完成视觉分析"、真实 `answer`、模型名、request_id、token 使用量 |
| 5 | 更换不同画面后再提交 | 回答随之变化（说明模型真的看到了图） |
| 6 | 故意把 `ARK_API_KEY` 设为空 | 500 "后端未配置 ARK_API_KEY" |
| 7 | 故意把 `ARK_API_KEY` 设为错误值 | 401 "视觉模型鉴权失败" |
| 8 | 故意把 `ARK_MODEL` 设为错误值 | 404 "模型名称不被识别" |
| 9 | 提交期间点击提交按钮 | 按钮 `disabled`，不重复调用 |
| 10 | 关闭后端再提交 | 友好提示"网络异常" |
| 11 | 多次提交不同问题 | 每次只产生一次模型请求（DevTools Network 验证） |
| 12 | 后端目录检查 | 没有保存任何图片文件 |
| 13 | 后端日志 | 不含 API Key、Authorization、图片 Base64 |
| 14 | `ARK_API_BASE` 配置成 `https://ark.cn-beijing.volces.com/api/v3` | 后端拒绝：`config_error`，500 |

### 10.4 构建验证

```bash
cd frontend
npm run build
```

### 10.5 后端语法检查

```bash
cd d:\2026qiniu2
python -m compileall backend
```

## 11. 当前限制

- **不实现多轮对话 / 上下文记忆**：每次提交都是独立的视觉问答。
- **不实现 AI 语音朗读**：留给 PR7。
- **不实现请求节流**：由前端按钮 `disabled` 防重入保证。
- **不实现按问题类型路由**：当前所有"涉及画面"的问题都走视觉模型（已经满足"用户主动截图后必然包含画面信息"的语义）。
- **不实现图片持久化 / 数据库**：图片只停留在内存，刷新即丢失。
- **不实现图片历史 / 多会话**：留给后续 PR。

## 12. 关键文件

| 文件 | 状态 |
| --- | --- |
| `backend/main.py` | 修改：调用 `call_vision_model`，统一错误返回 |
| `backend/requirements.txt` | 修改：新增 `httpx`、`python-dotenv` |
| `backend/.env.example` | 新建：环境变量模板（不含真实 Key） |
| `backend/services/__init__.py` | 新建：服务层包 |
| `backend/services/vision_model.py` | 新建：Coding Plan 视觉模型客户端 |
| `frontend/src/App.vue` | 修改：展示真实 AI 回答、token 用量、模型名 |
| `README.md` | 修改：标记 PR6 完成、补充配置说明 |
| `docs/pr-6.md` | 新建：本文档 |

## 13. 后续 PR

### PR7 - 语音合成朗读

- 浏览器端 Web Speech API `SpeechSynthesis`。
- 朗读模型返回的 `answer` 文本。
- 用户可点击"停止朗读"。
- 不上传文本到云端 TTS（成本控制）。

### PR8 - 端到端成本与隐私设计文档

- 把端云协同流程、节流策略、Key 管理、隐私边界汇总为正式设计文档（对应比赛要求的设计文档）。
