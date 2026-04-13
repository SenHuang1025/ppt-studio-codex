# 架构设计

## 整体架构

```text
Electron App
├── 渲染进程 (Chromium)
│   └── Vue3 SPA
│       ├── Dashboard 页
│       ├── Workspace 页
│       │   ├── Chat Panel（对话面板）
│       │   ├── Outline Panel（大纲面板）
│       │   ├── Preview Panel（预览面板）
│       │   └── PageNav Panel（缩略图导航）
│       └── Settings 页
│
├── 主进程 (Node.js)
│   ├── 窗口管理
│   ├── IPC 通信桥
│   ├── Python Sidecar 生命周期管理
│   ├── Preview Server 生命周期管理
│   ├── 本地文件系统操作
│   └── 安全存储（API Key 加密）
│
├── Python Sidecar（独立子进程）
│   └── FastAPI Server (localhost:18922)
│       ├── REST API（项目 CRUD、文件上传）
│       ├── SSE 端点（Agent 流式输出）
│       ├── LangGraph Agent System
│       │   └── Optional Deliberation Layer（可选思辨层）
│       ├── File Parsers
│       ├── SQLite Database
│       └── ChromaDB Vector Store
│
└── Preview Sandbox（本地 Vite Dev Server）
    └── localhost:18921
        ├── slide 路由
        ├── 主题变量
        └── 预装 PPT 组件
```

## 进程通信

```text
渲染进程 (Vue3)
    │
    ├── Electron IPC ──→ 主进程 (Node.js)
    │   用途：窗口操作、文件对话框、安全存储、服务地址获取
    │
    ├── HTTP / SSE ──→ Python Sidecar (FastAPI)
    │   用途：所有业务逻辑、Agent 交互、文件处理
    │   端口：localhost:18922
    │   认证：本地 token（启动时生成）
    │
    └── iframe ──→ Preview Sandbox (Vite)
        用途：渲染 Agent 生成的 Vue SFC 页面
        端口：localhost:18921
```

## 数据流

### 创建阶段数据流

```text
用户输入消息 + 上传文件
    ↓
POST /api/projects/{id}/agent/chat (SSE)
    ↓
Orchestrator Agent 判断意图
    ↓ (如果有新文件)
File Analyzer Agent
    → 调用对应 Parser 解析文件
    → 结构化数据存入 parsed/ 目录
    → 关键内容存入 ChromaDB
    ↓
Planner Agent
    → 如果开启多智能体思辨模式：
      Draft → Critic / Reviewer → Synthesis
    → 结合文件内容 + 用户需求
    → 生成 PPT 大纲 JSON
    → SSE 推送大纲到前端
    ↓ (用户确认大纲后)
Page Generator Agent（逐页）
    → 读取页面规划 + 全局主题 + 相关数据
    → 生成 Vue3 SFC 代码
    → 代码保存到 pages/ 目录
    → SSE 推送代码到前端
    → 前端 iframe 实时渲染预览
```

### 优化阶段数据流

```text
用户在预览页对第 N 页发送优化指令
    ↓
POST /api/projects/{id}/agent/chat (SSE)
    body: { message, page_number }
    ↓
Page Optimizer Agent
    → 如果开启多智能体思辨模式：
      Draft → Critic / Reviewer → Synthesis
    → 读取当前页 Vue 代码
    → 读取该页对话历史
    → 理解用户修改意图
    → 生成修改后的完整 Vue 代码
    → 旧版本备份到 versions/ 目录
    → 新代码写入 pages/ 目录
    → SSE 推送更新到前端
    → 前端 iframe 热刷新
```

## 安全设计
- Python Sidecar 只监听 `127.0.0.1`，不暴露到网络
- 每次启动生成随机 token，HTTP 请求需携带
- API Key 使用 Electron `safeStorage` 加密存储
- iframe 预览使用 `sandbox` 属性隔离
