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
│   └── pr-4.md             # PR4 文档
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

### PR5 - 视觉问答接口
- 上传压缩后的截图 Blob 到 FastAPI
- 接收用户问题文本
- 调用多模态 AI 模型
- 返回文本回答

### PR6 - 语音合成朗读
- 将文字回复转为语音
- 播放 AI 回复

### PR7 - 成本控制优化
- 多轮对话复用最近一次视觉摘要
- 请求节流
- 简单问题优先文本模型

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
