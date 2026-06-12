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
│   └── DESIGN.md           # 系统设计
└── README.md               # 项目说明
```

## 当前 PR1 完成内容

✅ 创建前后端分离项目骨架  
✅ 前端：Vue3 + Vite 项目初始化  
✅ 后端：FastAPI 最小服务，提供 /api/health 接口  
✅ 项目结构和配置文件  

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

### PR2 - 摄像头调用功能
- 实现摄像头权限请求
- 实时摄像头预览
- 拍照功能

### PR3 - 麦克风和语音识别
- 实现麦克风权限请求
- 语音录制
- 语音转文字

### PR4 - AI 模型调用
- 调用多模态 AI 模型
- 处理文本和图片输入
- 生成回复

### PR5 - 语音合成
- 将文字回复转为语音
- 播放 AI 回复

### PR6 - 成本控制优化
- 图片压缩
- 模型调用策略
- 请求节流

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
