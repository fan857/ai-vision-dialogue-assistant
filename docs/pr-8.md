# PR8 - 实时语音视觉对话

## 目标

让用户可以**对着 AI 说话**完成提问，AI 用**流式语音**回答；提问如果涉及画面，AI 会自动调用豆包视觉工具分析用户之前截取的摄像头画面。

整体分工：

| 角色 | 职责 |
|---|---|
| **Qwen3.5-Omni-Flash-Realtime** | 实时收音、用户语音转写、判断是否需要看图、流式 AI 文本 + 音频 |
| **Coding Plan Doubao-Seed-2.0-Pro**（PR6） | 收到 Qwen 工具调用后，分析摄像头截图并返回真实视觉答案 |
| **浏览器 `window.speechSynthesis`**（PR7） | 实时功能不可用时的**备用朗读方案**，不影响 PR6/PR7 文字路径 |

> ⚠️ **图片只发给豆包一次**。**不向 Qwen 发送图片**，避免重复视觉 token。

## 架构

```
┌──────────────┐    ① 麦克风 PCM (16kHz/16bit/mono)
│   Vue3       │ ────────────────────────────────────► ② FastAPI WebSocket
│  + AudioWorklet│   ◄──── 24kHz PCM 音频 + 文本事件 ───┘
│  + PCM Player │                                          │
└──────────────┘                                          │ ③ WebSocket
                                                          ▼
                                              ┌─────────────────────┐
                                              │  DashScope Realtime │
                                              │  qwen3.5-omni-...   │
                                              └─────────┬───────────┘
                                                        │ ④ 工具调用
                                                        │ analyze_current_frame
                                                        ▼
                                              ┌─────────────────────┐
                                              │  Doubao Vision API  │
                                              │  (PR6)              │
                                              └─────────┬───────────┘
                                                        │ ⑤ 真实视觉答案
                                                        ▼
                                                       Qwen
```

## 安全设计

- 浏览器 → FastAPI → 阿里云百炼，**API Key 不出后端**
- 前端通过本地相对路径 `ws://<host>/ws/realtime-voice`（开发由 Vite 代理转发到后端）
- 截图 base64 仅在 WebSocket session 内存中存在，**会话关闭立即释放**
- 不向 Qwen 发送图片
- 日志不输出图片 base64、API Key、Authorization 头

## 关键文件

| 文件 | 作用 |
|---|---|
| `backend/services/qwen_realtime.py`（新增） | Qwen Realtime 客户端：session.update、音频转发、Function Calling |
| `backend/main.py` | 新增 `WS /ws/realtime-voice` 端点 |
| `backend/requirements.txt` | 新增 `websockets==12.0` |
| `backend/.env.example` | 新增 DashScope 实时语音配置占位 |
| `frontend/src/audio/pcm-worklet.js`（新增） | AudioWorklet 处理器：16kHz/16bit PCM 上行 |
| `frontend/src/audio/pcm-player.js`（新增） | 24kHz PCM 流式播放（队列 + 单 AudioContext） |
| `frontend/src/App.vue` | 新增"实时语音视觉对话"区域 + 状态机 + 生命周期清理 |
| `frontend/vite.config.js` | 新增 `/ws` WebSocket 代理 |
| `docs/pr-8.md` | 本文档 |
| `tests/test_pr8_ws.py` | 后端 WebSocket 协议结构测试（7 个用例） |

## Qwen 会话配置（`qwen_realtime.py`）

| 项 | 值 |
|---|---|
| 模型 | `qwen3.5-omni-flash-realtime` |
| 端点 | `wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=...` |
| 鉴权 | `Authorization: Bearer DASHSCOPE_API_KEY` |
| 输出模态 | `["text", "audio"]` |
| 输入音频 | `pcm16`（16kHz/16bit/mono） |
| 输出音频 | `pcm16`（24kHz/16bit/mono） |
| 转写 | `gummy-realtime-v1` |
| VAD | `semantic_vad` |
| 联网搜索 | **关闭** |
| 工具 | `analyze_current_frame`（Function Calling） |
| 声音 | `Tina`（默认，可在 `QWEN_REALTIME_VOICE` 覆盖） |

### 系统提示词

```
你是 AI 视觉语音助手。
当用户询问当前画面中的人物、物体、文字、动作、位置或场景时，
必须调用 analyze_current_frame 工具，不要自行猜测图片内容。
获得工具结果后，用简洁、自然、适合口语朗读的中文回答。
非视觉问题可以直接回答。
```

### 工具定义

```json
{
  "type": "function",
  "name": "analyze_current_frame",
  "description": "当用户询问当前摄像头截图中的人物、物体、文字、动作、位置或场景时调用。返回该画面针对问题的真实视觉理解结果。",
  "parameters": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "用户针对当前画面的具体问题"
      }
    },
    "required": ["question"]
  }
}
```

## WebSocket 协议

### 客户端 → 服务端

| 帧类型 | 类型 | 内容 |
|---|---|---|
| Text (JSON) | `session.init` | `{type, image_base64, content_type}` |
| Binary | - | 16kHz/16bit/mono PCM 音频（每帧约 100ms = 1600 samples = 3200 bytes） |
| Text (JSON) | `cancel` | 取消当前响应（仅停止播放，不结束会话） |
| Text (JSON) | `ping` | 心跳 |

### 服务端 → 客户端

| 帧类型 | 类型 | 内容 |
|---|---|---|
| Text (JSON) | `session.ready` | 会话已建立，可以开始说话 |
| Text (JSON) | `session.error` | 错误信息，附带 `message` |
| Binary | - | 24kHz/16bit/mono PCM 音频片段（按到达顺序播放） |
| Text (JSON) | `*` | Qwen Realtime 事件透传（`response.audio_transcript.delta` 等） |
| Text (JSON) | `vision.analyzing` | 服务端正在调用豆包视觉 |
| Text (JSON) | `vision.analyzed` | 豆包视觉调用完成 |
| Text (JSON) | `server.error` | Qwen 上游错误（不立即 fail） |
| Text (JSON) | `server.disconnected` | 连接关闭 |
| Text (JSON) | `pong` | 心跳响应 |

## 音频采集（前端）

通过 **AudioWorklet**：

1. `navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, ... } })`
2. 创建 `AudioContext`
3. `audioWorklet.addModule('./audio/pcm-worklet.js')`
4. `createMediaStreamSource(mic)` → `AudioWorkletNode('pcm16k-processor')`
5. 在 worklet 里：**线性重采样**到 16kHz，转换为 **Int16 PCM**，每 100ms 通过 `port.postMessage(buf)` 发送
6. 主线程把 ArrayBuffer 直接通过 WebSocket 二进制帧转发

> **二进制帧不经过 Base64**。这避免了 4/3 的网络膨胀和额外的 CPU 编码开销。

## 音频播放（前端）

通过自实现的 `PCMStreamPlayer`：

1. 单一 `AudioContext`（`{ sampleRate: 24000 }`）
2. 收到二进制帧后 Int16 → Float32，构造 `AudioBuffer`
3. 推入 `queue` 数组
4. `_scheduleNext()` 取队首 → `createBufferSource` → 连接到 `destination` → `start(0)`
5. 监听 `onended` 自动播下一段

停止播放：`stop()` 清空队列 + 停掉当前 source。

## Function Calling 流程

```
Qwen: <tool_call>
  analyze_current_frame(question="我手里拿的是什么？")
</tool_call>

→ 后端：解析 function_call 参数
→ 后端：调用 Doubao 视觉服务（PR6 call_vision_model）
  传入当前会话保存的截图 + question
→ 后端：拿到真实视觉答案
→ 后端：发送 conversation.item.create
  item: { type: "function_call_output", call_id, output: 真实答案 }
→ 后端：发送 response.create
→ Qwen：根据工具结果组织自然语言回答
→ Qwen：流式返回 text + audio
→ 前端：实时显示文字 + 播放音频
```

**关键：图片不发给 Qwen。** 后端在收到 function_call 时，从会话内存里取出开始时浏览器传来的截图（base64 已解码为 bytes）。

## 状态机

```
idle → connecting → listening → recognizing → answering → playing → listening
                                     ↓
                                  analyzing → answering
```

| 状态 | 含义 |
|---|---|
| `idle` | 未开始 |
| `connecting` | 正在与后端/Qwen 建立连接 |
| `listening` | 已就绪，等待用户说话 |
| `recognizing` | Qwen 正在识别用户语音 |
| `analyzing` | 正在调用豆包视觉分析画面 |
| `answering` | Qwen 正在生成回答文本 |
| `playing` | 正在播放 AI 回答 |
| `ended` | 用户主动结束或连接断开 |
| `failed` | 连接失败、Key 缺失、麦克风不可用等 |

## 生命周期清理（前端）

`onBeforeUnmount` 中：

1. 关闭 WebSocket
2. 停止所有麦克风 track
3. 断开 worklet 节点
4. 关闭 `AudioContext`
5. 关闭 PCM 播放器（清理队列 + 关闭 AudioContext）

点击「结束会话」时执行同样的清理。

## 成本控制

| 措施 | 说明 |
|---|---|
| 图片只发一次 | 截图随 session.init 上传一次，**绝不重复发给 Qwen** |
| 不开联网搜索 | system prompt 中不开启 search 工具 |
| 音频按需上传 | 仅在用户点击「开始实时对话」期间上传 PCM；结束会话立即停止 |
| 不自动重连 | 失败时显示错误，要求用户手动重试 |
| 不同时播放 PR7 | 若实时功能失败，由 PR7 浏览器 TTS 兜底 |
| 实时失败不影响文字 | 文字视觉问答（PR5/PR6）路径完全独立 |
| 截图内存隔离 | 截图 base64 仅在当前 WS 会话内存中存在 |

## 隐私设计

- 截图 base64 不落盘、不写日志、不入库
- 音频按 binary 帧直发，不经过 base64
- API Key 仅在后端，从 `backend/.env` 读取（`.gitignore` 已忽略）
- WebSocket 鉴权：浏览器只连本地后端，**无法直接连百炼**

## 测试

### 自动化测试（不需外网/真实 Key）

```bash
cd d:\2026qiniu2
python -m pytest tests/test_pr8_ws.py -v
```

应输出 `7 passed`。覆盖：
- 路由注册
- 缺图片字段 / 非法 base64
- 缺 `DASHSCOPE_API_KEY`
- 图片超 2 MB
- ping/pong
- 初始化前 binary 帧被静默忽略

### 构建验证

```bash
cd frontend
npm run build        # 必须成功
```

```bash
cd backend
python -m compileall backend   # 必须成功
```

### 端到端测试（需要真实 `DASHSCOPE_API_KEY`）

1. 在 `backend/.env` 填入真实 DashScope（北京）API Key
2. 启动后端 + 前端（参考 README）
3. 打开摄像头，截取当前画面
4. 点击「开始实时对话」，允许麦克风权限
5. 用普通中文提问（"你好"），听 AI 回答
6. 问画面相关问题（"我手里拿的是什么？"），观察 Qwen 是否触发视觉分析
7. 点击「停止当前播放」立即停止
8. 点击「结束会话」关闭所有资源

## 当前限制

- **不持久化**会话：刷新页面、关闭浏览器后会话状态丢失
- **不并发多会话**：同一时间只支持一个实时会话
- **不优化响应延迟**：模型速度取决于 DashScope 服务端
- **不支持打断恢复**：用户开始说话时不会自动 stop AI 当前播放（PR8 简化处理）
- **不支持音色选择 UI**：使用 `QWEN_REALTIME_VOICE` 环境变量配置
- **不支持 Function Calling 工具链扩展**：只暴露 `analyze_current_frame`

## 与 PR7 的协同

| 场景 | 行为 |
|---|---|
| 实时功能可用 | 使用 Qwen 实时语音 |
| Qwen 连接失败 / Key 缺失 | 显示错误，提示用户改用「视觉问答」+「AI 回答语音合成」 |
| 实时进行中出错 | 不影响 PR6 文字视觉问答；用户可继续手动提问 |
| 实时进行中用户切换到文字问答 | 实时会话和文字会话相互独立，可同时使用 |

## PR 描述草稿

> **feat: 接入 Qwen3.5 Omni 实时视觉语音对话**
>
> 引入阿里云百炼 Qwen3.5-Omni-Flash-Realtime 模型，让用户可以**对着 AI 说话**完成提问，AI 用**流式语音**实时回答。涉及画面时，Qwen 自动调用豆包视觉工具（PR6）分析摄像头截图。
>
> **核心改进**：
> 1. 后端 `WS /ws/realtime-voice`：连接百炼 Realtime，转发 PCM 音频，处理 Function Calling
> 2. 前端 AudioWorklet：麦克风实时采集 + 16kHz/16bit/mono PCM 上行
> 3. 前端 PCM Stream Player：24kHz 音频分片排队播放，无重叠
> 4. 工具调用 `analyze_current_frame` 复用 PR6 Doubao 视觉服务
> 5. PR7 浏览器 TTS 仍保留为实时不可用时的备用方案
>
> **安全**：API Key 仅在后端；截图 base64 仅在 WS 会话内存中；日志不含 Key/Base64。
>
> **成本**：图片只发一次（只给豆包），不向 Qwen 重复发；不开启联网搜索；按需上传音频。
