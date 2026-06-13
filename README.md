# AI 视觉对话助手

## 项目背景

本项目参加七牛云 × XEngineer 暑期实训营最后一批议题。

## 所选题目

题目一：AI 视觉对话助手

## 项目结构

```
├── frontend/               # Vue3 + Vite 前端
│   ├── src/                # 源代码
│   │   ├── App.vue         # 主应用组件
│   │   ├── main.js         # 应用入口
│   │   └── style.css       # 全局样式
│   ├── index.html          # 入口 HTML
│   ├── vite.config.js      # Vite 配置
│   └── package.json        # 依赖配置
├── backend/                # Python FastAPI 后端
│   ├── main.py             # 主服务文件
│   ├── requirements.txt    # Python 依赖
│   ├── .env.example        # 环境变量示例
│   └── services/           # 业务服务层
│       └── vision_model.py # 视觉模型调用
├── docs/                   # 设计文档
│   ├── pr-2.md             # PR2 文档
│   ├── pr-3.md             # PR3 文档
│   ├── pr-4.md             # PR4 文档
│   ├── pr-5.md             # PR5 文档
│   ├── pr-6.md             # PR6 文档
│   ├── pr-7.md             # PR7 文档
│   └── pr-8.md             # PR8 文档
└── README.md               # 项目说明
```

## 当前完成内容

### PR1 - 项目骨架初始化

✅ 创建前后端分离项目骨架  
✅ 前端：Vue3 + Vite 项目初始化  
✅ 后端：FastAPI 最小服务，提供 /api/health 接口  
✅ 项目结构和配置文件  

### PR2 - 摄像头实时预览功能

✅ 实现摄像头权限请求  
✅ 实时摄像头预览  
✅ 拍照功能（预留）  
✅ 状态显示和错误处理  

### PR3 - 麦克风语音识别功能

✅ 集成浏览器 Web Speech API（`SpeechRecognition` / `webkitSpeechRecognition`）  
✅ 语音识别语言设置：中文（`zh-CN`）  
✅ 开始/停止识别按钮 + 状态显示（未开始/请求中/识别中/完成/失败/不支持）  
✅ 识别结果实时显示在页面（"识别到的问题"区域）  
✅ 手动输入框 fallback（与识别结果共用 `userQuestionText` 状态）  
✅ 浏览器不支持 / 权限拒绝 / 网络错误等场景的友好提示

### PR4 - 摄像头截图与前端图片压缩

✅ 用户主动截取当前摄像头画面（按钮：截取当前画面）  
✅ 浏览器端 JPEG 压缩：最长边 1280px，质量 0.75  
✅ 生成压缩后的 Blob 和 Object URL 预览（自动释放旧 URL，避免内存泄漏）  
✅ 页面显示原始尺寸、压缩后尺寸、文件大小（KB/MB）、图片类型、截图时间  
✅ 摄像头未开启时截图按钮禁用，并给出友好提示  
✅ "清除截图"按钮：清除预览和元数据，不关闭摄像头  
✅ 成本控制：只在用户主动点击时截取一帧，不上传视频流  
✅ 隐私说明：明确提示用户视频不会持续上传，上传前会压缩  
⚠️ 当前图片仅保存在浏览器内存中，**尚未上传到后端**，**未调用任何 AI 模型**

### PR5 - 前后端视觉对话请求链路

✅ FastAPI `POST /api/vision-dialogue` 接口（`multipart/form-data`）  
✅ 前端 `FormData` 提交 `question`（用户问题）+ `image`（压缩后 Blob）  
✅ Vite 开发代理：`/api` → `http://localhost:3001`  
✅ 后端校验：问题非空且 ≤ 1000 字符、图片格式（JPEG/PNG/WebP）、图片大小 ≤ 2 MB  
✅ 后端计算图片 SHA-256、生成 UUID `request_id`、返回请求接收结果  
✅ 前端状态管理：未提交 / 提交中 / 成功 / 失败  
✅ 友好错误提示：优先展示后端 `detail`，网络异常给明确提示  
✅ 成本控制：图片仅在用户主动提交时上传，不落盘、不持久化、不调用 AI  
⚠️ **当前尚未接入 AI 多模态模型**，仅完成请求链路验证

### PR6 - 接入火山方舟 Coding Plan Doubao-Seed-2.0-Pro 视觉模型

✅ 后端新增 `backend/services/vision_model.py`，使用 `httpx` 异步调用 `/chat/completions`  
✅ 固定使用 Coding Plan 端点：`https://ark.cn-beijing.volces.com/api/coding/v3`（禁止切换到 `/api/v3`）  
✅ 模型名：`doubao-seed-2.0-pro`（从环境变量 `ARK_MODEL` 读取）  
✅ 通过 `python-dotenv` 加载 `backend/.env`，API Key 仅保存在本地，不进仓库  
✅ 多模态请求：`image_url`（Base64 Data URL）+ 用户文本，超时 60s，最大 300 tokens  
✅ 错误处理：区分鉴权失败 / Coding Plan 无权限 / 模型名错误 / 不支持图片 / 超时 / 限流 / 上游 5xx / 响应结构异常 / 回答为空  
✅ 日志只记录 `request_id`、状态码、错误类型，**不记录 API Key、Authorization 头或图片 Base64**  
✅ 成功响应包含真实 `answer`（来自模型）、`model`、`request_id`、`usage`（仅在上游返回时显示）  
✅ 前端展示真实 AI 回答、模型名、request_id、Token 使用量  
✅ 提交中显示："AI 正在分析当前画面……"  
✅ 成功后顶部提示："AI 已完成视觉分析"  
⚠️ 当前不实现多轮对话、上下文记忆、AI 语音朗读

### PR8 - 实时语音视觉对话（Qwen3.5-Omni-Flash-Realtime + 豆包视觉）

✅ 引入阿里云百炼 `qwen3.5-omni-flash-realtime` 实现**对着 AI 说话**的实时对话
✅ 后端 `WS /ws/realtime-voice`：连接 DashScope Realtime，转发 PCM 音频，处理 Function Calling
✅ 前端 **AudioWorklet** 采集 16kHz/16bit/mono PCM，WebSocket **二进制帧**直发（不走 base64）
✅ 前端自实现 **PCM Stream Player**：24kHz 音频分片按顺序排队播放，无重叠，单 AudioContext 复用
✅ Function Calling：注册 `analyze_current_frame` 工具，**复用 PR6 豆包视觉服务**分析摄像头截图
✅ **图片只发给豆包一次**，**不向 Qwen 发送图片**，避免重复视觉 token
✅ 音频：输入 pcm16/16kHz、输出 pcm16/24kHz、声音 Tina、可在 `QWEN_REALTIME_VOICE` 覆盖
✅ 状态机：未开始 / 正在连接 / 聆听 / 识别 / 分析画面 / 回答 / 播放 / 已结束 / 失败
✅ 控件：开始实时对话 / 结束会话 / 停止当前播放；停止播放会向后端发 `cancel` 取消当前响应
✅ 生命周期：`onBeforeUnmount` 中关闭 WebSocket、停止麦克风、断开 worklet、关闭 AudioContext
✅ 实时失败时**不影响** PR5/PR6/PR7 文字路径；**PR7 浏览器 TTS 仍保留为备用朗读方案**
⚠️ 需要 `backend/.env` 中配置 `DASHSCOPE_API_KEY`
⚠️ 端到端真实测试需要用户本地用真实 DashScope Key 完成（沙箱无 Key 无外网）
⚠️ 当前不实现多会话历史、打断恢复续说、音色选择 UI

### PR7 - AI 回答语音合成与朗读

✅ 使用浏览器原生 `window.speechSynthesis` + `SpeechSynthesisUtterance`，**不接入云端 TTS**  
✅ **不**新增 API Key、**不**产生额外费用、**不**上传 AI 回答到第三方  
✅ 朗读 AI 回答的 `answer` 字段（不朗读 request_id、Token、图片大小等元数据）  
✅ 中文 voice 优先选择：先 `zh-CN`，再 `zh-TW`/`zh-HK`，最后回退到浏览器默认 voice  
✅ 兼容部分浏览器 `getVoices()` 首次返回空：通过 `onvoiceschanged` 事件重新加载  
✅ 控件：朗读回答、停止朗读、自动朗读 AI 回答 复选框  
✅ 朗读状态：未朗读 / 正在朗读 / 已完成 / 已停止 / 不支持 / 朗读失败  
✅ 自动朗读：新视觉问题成功后，若开关开启则自动朗读新回答；新请求前先 `cancel()` 旧朗读  
✅ 手动朗读：可随时点击「朗读回答」重新朗读；正在朗读时按钮禁用避免重复触发  
✅ 生命周期：组件卸载时 `speechSynthesis.cancel()`，并移除 `onvoiceschanged` 监听  
✅ 浏览器不支持时显示提示，朗读失败不影响文字回答，截图与问题不被清空  
⚠️ 不同系统 / 浏览器内置中文音色差异较大，效果取决于客户端  
⚠️ 当前不实现多轮对话、上下文记忆、自定义音色 / 语速持久化、音频文件下载

## 前端运行方式

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

## 后端运行方式

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 3001
```

访问：http://localhost:3001/api/health

## 后续计划

MVP 链路已完成（PR1 → PR8）。后续如需继续迭代，可考虑：

- 设计文档 `DESIGN.md`：汇总用户故事、端云协同、成本控制、用户故事完成情况
- 多轮对话 / 上下文记忆（复用最近一次视觉摘要）
- 朗读历史 / 朗读速度 / 音调持久化
- 实时对话打断恢复 + 音色选择 UI
- 错误时引导重试 + AbortController 取消正在进行的模型请求

⚠️ MVP 范围内不引入登录注册、数据库、后台管理系统等与题目无关的能力。

## 成本控制策略

1. 不上传连续视频流，只在用户提问时截取当前帧
2. 图片上传前进行压缩（PR4：最长边 1280px，JPEG 质量 0.75）
3. 后端限制最大 2 MB（PR5 校验）
4. 视觉模型调用固定使用 Coding Plan 端点（`/api/coding/v3`），禁止自动切换到 `/api/v3`
5. `max_tokens = 300`，单次回答有上限
6. 用户点击一次只调用一次模型，**不自动重试**
7. 多轮对话复用最近一次视觉摘要（后续 PR）
8. API Key 放在环境变量中，**永不提交到仓库**

## 技术栈

前端：Vue3 + Vite + JavaScript  
后端：Python + FastAPI + httpx + python-dotenv  
视觉模型：火山方舟 Coding Plan Doubao-Seed-2.0-Pro（`https://ark.cn-beijing.volces.com/api/coding/v3`）  
部署：待确定  

## 配置本地后端

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入真实的 ARK_API_KEY（其余可用默认值）
pip install -r requirements.txt
uvicorn main:app --reload --port 3001
```

⚠️ 真实 `ARK_API_KEY` 不能写入代码、README、日志或 Git。`.env` 已在 `.gitignore` 中。
