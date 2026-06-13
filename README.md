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
│   └── requirements.txt    # Python 依赖
├── docs/                   # 设计文档
│   ├── pr-2.md             # PR2 文档
│   ├── pr-3.md             # PR3 文档
│   ├── pr-4.md             # PR4 文档
│   └── pr-5.md             # PR5 文档
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

### PR6 - 接入多模态 AI 模型
- 后端调用多模态大模型，理解图片内容 + 用户问题
- 返回 AI 生成的文本回复
- 简单问题不调用视觉模型（成本控制）
- 多轮对话复用最近一次视觉摘要

### PR7 - 语音合成朗读
- 将 AI 文本回复转为语音
- 浏览器端 TTS 播放

## 成本控制策略

1. 不上传连续视频流，只在用户提问时截取当前帧
2. 图片上传前进行压缩
3. 只在问题涉及画面时调用视觉模型
4. 多轮对话中复用最近一次视觉摘要
5. 对请求进行节流，避免频繁调用模型
6. API Key 放在环境变量中，不提交到仓库

## 技术栈

前端：Vue3 + Vite + JavaScript  
后端：Python + FastAPI  
部署：待确定  
