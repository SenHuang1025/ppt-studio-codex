# PPT Studio - 项目总览

## 一句话描述
AI Agent 驱动的 PPT 生成桌面应用，用户通过自然语言对话 + 上传文件，自动生成基于 Vue3 的交互式演示文稿。

## 核心用户流程

```text
用户新建项目 → 上传文件 + 描述需求 → Agent 分析文件内容
→ Agent 规划 PPT 大纲 → 用户确认 / 调整大纲
→ Agent 逐页生成 Vue3 代码 → 用户预览 PPT
→ 用户逐页浏览，针对当前页与 Agent 对话优化
→ 完成，导出 / 分享
```

## 三大核心页面

### 1. Dashboard（项目首页）
- 展示所有 PPT 项目卡片
- 状态：规划中 / 生成中 / 创作中 / 已完成
- 支持新建、删除、归档项目

### 2. Workspace - 对话模式（创建 / 规划阶段）
- 左侧：Agent 对话区域，支持文件上传
- 右侧：PPT 大纲实时更新面板
- Agent 工作流：文件分析 → 大纲规划 → 确认 → 逐页生成

### 3. Workspace - 预览模式（优化阶段）
- 左侧：页面缩略图导航栏，带状态标识
- 中央：PPT 页面预览区，支持翻页、全屏
- 右侧：针对当前页的快捷操作栏 + 对话优化区

## 关键技术亮点
1. **Agent 多层架构**：主编排 + 文件分析 + 规划 + 生成 + 优化，并支持可选的多智能体思辨模式
2. **Vue SFC 运行时渲染**：Agent 生成的 `.vue` 代码在 iframe 沙箱中实时预览
3. **流式交互**：SSE 推送 Agent 思考过程和生成进度
4. **全局主题系统**：CSS 变量驱动，一键换肤；当前默认应用壳体采用暖色自然、纸感、轻质的工作台主题，内容区保持稳定实色
5. **版本管理**：每页每次修改自动保存版本，可回滚对比

## 技术栈概要
- **桌面**：Electron + electron-vite
- **前端**：Vue3 + TypeScript + Naive UI + UnoCSS + ECharts + GSAP
- **后端**：FastAPI + LangGraph + LangChain
- **LLM**：OpenAI GPT 系列（主力）/ Claude Sonnet（备选，可通过 LiteLLM 切换）
- **存储**：SQLite + ChromaDB + 本地文件系统
- **文件解析**：openpyxl / python-docx / PyMuPDF / python-pptx / pandas
