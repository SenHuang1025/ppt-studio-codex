# 最佳方案：构建结构化项目文档体系

直接丢一个大"开发计划"给 Claude Code 效果不好——上下文太长它会丢失重点，文档太短它又缺乏理解。

**最优解是：建立一套分层的项目文档，让 Claude Code 在不同开发阶段读取对应文档。**

---

## 📁 文档体系结构

ppt-studio/
├── CLAUDE.md                          # Claude Code 专属指令文件（自动读取）
├── docs/
│   ├── 00-project-overview.md         # 项目全貌（一页纸说清楚）
│   ├── 01-architecture.md             # 架构设计
│   ├── 02-tech-stack.md               # 技术选型详情
│   ├── 03-agent-system.md             # Agent 系统设计
│   ├── 04-data-model.md               # 数据模型设计
│   ├── 05-api-design.md               # API 接口设计
│   ├── 06-ui-pages.md                 # 页面设计与交互
│   ├── 07-ppt-render-engine.md        # PPT 渲染引擎方案
│   └── development-phases/
│       ├── phase-1-foundation.md      # 第一阶段：基础骨架
│       ├── phase-2-agent-core.md      # 第二阶段：Agent 核心
│       ├── phase-3-ppt-engine.md      # 第三阶段：渲染引擎
│       ├── phase-4-optimization.md    # 第四阶段：优化交互
│       └── phase-5-polish.md          # 第五阶段：打磨发布
└── ...


---

## 📄 逐一生成每个文件

### `CLAUDE.md` — Claude Code 的总指挥


# CLAUDE.md - PPT Studio 项目指南

## 项目简介
PPT Studio 是一个基于 AI Agent 的 PPT 生成桌面应用。
用户通过对话+上传文件的方式，由 AI Agent 自动生成 Vue3 组件代码作为 PPT 页面。
技术栈：Electron + Vue3 + TypeScript + FastAPI + Python + LangGraph。

## 项目文档
开发前请先阅读 `docs/00-project-overview.md` 了解全貌。
各模块详细设计在 `docs/` 目录下，按编号排列。
分阶段开发计划在 `docs/development-phases/` 目录下。

## 项目结构

ppt-studio/
├── electron/                    # Electron 主进程
│   ├── main.ts
│   ├── preload.ts
│   └── sidecar/                 # Python 进程管理
├── src/                         # Vue3 前端（渲染进程）
│   ├── assets/
│   ├── components/
│   │   ├── common/              # 通用组件
│   │   ├── chat/                # 对话相关组件
│   │   ├── preview/             # PPT 预览相关组件
│   │   └── project/             # 项目管理相关组件
│   ├── composables/             # 组合式函数
│   ├── layouts/                 # 布局组件
│   ├── pages/                   # 页面
│   │   ├── dashboard/           # 项目列表首页
│   │   ├── workspace/           # 项目工作区（对话+预览）
│   │   └── settings/            # 设置页
│   ├── stores/                  # Pinia 状态
│   ├── services/                # API 调用层
│   ├── types/                   # TypeScript 类型
│   ├── utils/                   # 工具函数
│   ├── router/                  # 路由配置
│   ├── App.vue
│   └── main.ts
├── python-backend/              # Python 后端
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/                 # API 路由
│   │   │   ├── projects.py
│   │   │   ├── agent.py
│   │   │   ├── files.py
│   │   │   └── preview.py
│   │   ├── agents/              # LangGraph Agent 系统
│   │   │   ├── orchestrator.py  # 主编排 Agent
│   │   │   ├── file_analyzer.py # 文件分析 Agent
│   │   │   ├── planner.py       # 大纲规划 Agent
│   │   │   ├── page_generator.py# 页面生成 Agent
│   │   │   ├── page_optimizer.py# 页面优化 Agent
│   │   │   ├── graph.py         # LangGraph 工作流定义
│   │   │   └── prompts/         # Agent 提示词
│   │   ├── services/            # 业务逻辑
│   │   │   ├── project_service.py
│   │   │   ├── file_service.py
│   │   │   └── render_service.py
│   │   ├── parsers/             # 文件解析器
│   │   │   ├── excel_parser.py
│   │   │   ├── word_parser.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── pptx_parser.py
│   │   │   └── image_parser.py
│   │   ├── models/              # 数据库模型
│   │   ├── schemas/             # Pydantic Schema
│   │   ├── db/                  # 数据库配置
│   │   └── config.py            # 配置
│   ├── pyproject.toml
│   └── README.md
├── docs/                        # 项目文档（详见上方）
├── resources/                   # Electron 打包资源
├── package.json
├── electron.vite.config.ts
├── tsconfig.json
├── uno.config.ts
└── CLAUDE.md



## 开发规范

### 前端
- 使用 Vue3 Composition API + `<script setup>` 语法
- 组件文件名使用 PascalCase：`ProjectCard.vue`
- 组合式函数以 `use` 开头：`useProject.ts`
- 使用 Naive UI 组件库，不要混用其他 UI 库
- CSS 优先使用 UnoCSS 原子类，复杂样式用 `<style scoped>`
- 所有变量和函数必须有 TypeScript 类型

### 后端
- 使用 async/await 异步编程
- API 路由按功能模块划分文件
- 所有接口入参/出参使用 Pydantic Schema 定义
- Agent Prompt 统一放在 `agents/prompts/` 目录
- 文件解析器实现统一的 `BaseParser` 接口
- 使用 Loguru 记录日志

### Git 提交规范
- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- style: 样式
- chore: 构建/工具

## 常用命令

# 前端开发
pnpm dev          # 启动 Electron 开发模式
pnpm build        # 构建

# Python 后端
cd python-backend
uv run fastapi dev app/main.py --port 18930

# 代码检查
pnpm lint         # 前端 lint
cd python-backend && uv run ruff check .  # Python lint


## 当前开发阶段
Phase 1 - 基础骨架搭建
详见 `docs/development-phases/phase-1-foundation.md`


---

### `docs/00-project-overview.md`


# PPT Studio - 项目总览

## 一句话描述
AI Agent 驱动的 PPT 生成桌面应用，用户通过自然语言对话 + 上传文件，自动生成基于 Vue3 的交互式演示文稿。

## 核心用户流程


用户新建项目 → 上传文件 + 描述需求 → Agent 分析文件内容
→ Agent 规划 PPT 大纲 → 用户确认/调整大纲
→ Agent 逐页生成 Vue3 代码 → 用户预览 PPT
→ 用户逐页浏览，针对当前页与 Agent 对话优化
→ 完成，导出/分享


## 三大核心页面

### 1. Dashboard（项目首页）
- 展示所有 PPT 项目卡片
- 状态：规划中 / 生成中 / 创作中 / 已完成
- 支持新建、删除、归档项目

### 2. Workspace - 对话模式（创建/规划阶段）
- 左侧：Agent 对话区域（支持文件上传）
- 右侧：PPT 大纲实时更新面板
- Agent 工作流：文件分析 → 大纲规划 → 确认 → 逐页生成

### 3. Workspace - 预览模式（优化阶段）
- 上方：PPT 页面预览区（支持翻页、全屏）
- 下方：针对当前页的快捷操作栏 + 对话优化区
- 底部：页面缩略图导航栏（带状态标识）

## 关键技术亮点
1. **Agent 多层架构**：主编排 + 文件分析 + 规划 + 生成 + 优化，5 个专职 Agent
2. **Vue SFC 运行时渲染**：Agent 生成的 .vue 代码在 iframe 沙箱中实时预览
3. **流式交互**：SSE 推送 Agent 思考过程和生成进度
4. **全局主题系统**：CSS 变量驱动，一键换肤，所有页面风格统一
5. **版本管理**：每页每次修改自动保存版本，可回滚对比

## 技术栈概要
- **桌面**：Electron + electron-vite
- **前端**：Vue3 + TypeScript + Naive UI + UnoCSS + ECharts + GSAP
- **后端**：FastAPI + LangGraph + LangChain
- **LLM**：Claude Sonnet（主力）/ GPT-4o（备选）
- **存储**：SQLite + ChromaDB + 本地文件系统
- **文件解析**：openpyxl / python-docx / PyMuPDF / python-pptx / pandas


---

### `docs/01-architecture.md`


# 架构设计

## 整体架构


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
│   ├── 本地文件系统操作
│   └── 安全存储（API Key 加密）
│
└── Python Sidecar（独立子进程）
    └── FastAPI Server (localhost:18930)
        ├── REST API（项目CRUD、文件上传）
        ├── SSE 端点（Agent 流式输出）
        ├── LangGraph Agent System
        │   ├── Orchestrator Agent
        │   ├── File Analyzer Agent
        │   ├── Planner Agent
        │   ├── Page Generator Agent
        │   └── Page Optimizer Agent
        ├── File Parsers
        ├── SQLite Database
        └── ChromaDB Vector Store


## 进程通信


渲染进程 (Vue3)
    │
    ├── Electron IPC ──→ 主进程 (Node.js)
    │   用途：窗口操作、文件对话框、安全存储
    │
    └── HTTP/SSE ──→ Python Sidecar (FastAPI)
        用途：所有业务逻辑、Agent 交互、文件处理
        端口：localhost:18930
        认证：本地 token（启动时生成）


## 数据流

### 创建阶段数据流

用户输入消息 + 上传文件
    ↓
POST /api/agent/chat (SSE)
    ↓
Orchestrator Agent 判断意图
    ↓ (如果有新文件)
File Analyzer Agent
    → 调用对应 Parser 解析文件
    → 结构化数据存入 parsed/ 目录
    → 关键内容存入 ChromaDB
    ↓
Planner Agent
    → 结合文件内容 + 用户需求
    → 生成 PPT 大纲 JSON
    → SSE 推送大纲到前端
    ↓ (用户确认大纲后)
Page Generator Agent (逐页)
    → 读取页面规划 + 全局主题 + 相关数据
    → 生成 Vue3 SFC 代码
    → 代码保存到 pages/ 目录
    → SSE 推送代码到前端
    → 前端 iframe 实时渲染预览


### 优化阶段数据流

用户在预览页对第 N 页发送优化指令
    ↓
POST /api/agent/optimize (SSE)
    body: { projectId, pageNumber, message }
    ↓
Page Optimizer Agent
    → 读取当前页 Vue 代码
    → 读取该页对话历史
    → 理解用户修改意图
    → 生成修改后的完整 Vue 代码
    → 旧版本备份到 versions/ 目录
    → 新代码写入 pages/ 目录
    → SSE 推送更新到前端
    → 前端 iframe 热刷新


## 安全设计
- Python Sidecar 只监听 127.0.0.1，不暴露到网络
- 每次启动生成随机 token，HTTP 请求需携带
- API Key 使用 Electron safeStorage 加密存储
- iframe 预览使用 sandbox 属性隔离


---

### `docs/02-tech-stack.md`


# 技术选型

## 桌面应用层
| 技术             | 版本   | 用途     |
| ---------------- | ------ | -------- |
| Electron         | 33+    | 桌面容器 |
| electron-vite    | 2.3+   | 构建工具 |
| electron-builder | 25+    | 打包发布 |
| electron-updater | latest | 自动更新 |

## 前端
| 技术               | 版本  | 用途               |
| ------------------ | ----- | ------------------ |
| Vue                | 3.5+  | UI 框架            |
| TypeScript         | 5.6+  | 类型安全           |
| Vite               | 6+    | 构建工具           |
| Vue Router         | 4.4+  | 路由               |
| Pinia              | 2.2+  | 状态管理           |
| Naive UI           | 2.39+ | UI 组件库          |
| UnoCSS             | 0.62+ | CSS 方案           |
| VueUse             | 11+   | 工具函数           |
| @vueuse/motion     | 2.2+  | 声明式动画         |
| GSAP               | 3.12+ | 高级动画           |
| ECharts            | 5.5+  | 图表               |
| vue-echarts        | 7+    | Vue 封装           |
| Monaco Editor      | 0.50+ | 代码编辑器（可选） |
| markdown-it        | 14+   | Markdown 渲染      |
| vue-draggable-plus | 0.5+  | 拖拽排序           |
| html2canvas        | 1.4+  | 截图               |
| jsPDF              | 2.5+  | PDF 导出           |
| @vue/compiler-sfc  | 3.5+  | SFC 运行时编译     |

## 后端
| 技术                | 版本   | 用途           |
| ------------------- | ------ | -------------- |
| Python              | 3.12+  | 运行时         |
| FastAPI             | 0.115+ | Web 框架       |
| Uvicorn             | 0.30+  | ASGI 服务器    |
| LangGraph           | 0.2+   | Agent 工作流   |
| LangChain           | 0.3+   | LLM 框架       |
| langchain-anthropic | 0.2+   | Claude 集成    |
| litellm             | 1.48+  | 多模型统一接口 |
| SQLAlchemy          | 2.0+   | ORM            |
| aiosqlite           | 0.20+  | 异步 SQLite    |
| ChromaDB            | 0.5+   | 向量数据库     |
| Pydantic            | 2.9+   | 数据校验       |
| sse-starlette       | 2.1+   | SSE 支持       |
| Loguru              | 0.7+   | 日志           |

## 文件解析
| 技术        | 文件类型        |
| ----------- | --------------- |
| openpyxl    | .xlsx           |
| pandas      | .csv + 数据分析 |
| python-docx | .docx           |
| PyMuPDF     | .pdf            |
| python-pptx | .pptx           |
| Pillow      | 图片            |

## 工程化
| 技术              | 用途            |
| ----------------- | --------------- |
| pnpm              | 前端包管理      |
| uv                | Python 包管理   |
| ESLint + Prettier | 前端代码规范    |
| Ruff              | Python 代码规范 |
| Vitest            | 前端测试        |
| pytest            | 后端测试        |


---

### `docs/03-agent-system.md`


# Agent 系统设计

## Agent 架构


用户消息
    ↓
┌─────────────────────────────┐
│   Orchestrator Agent        │
│   职责：意图识别、任务路由    │
│   模型：Claude Sonnet       │
└──────┬──────────────────────┘
       │ 根据意图路由到对应 Agent
       ├──→ File Analyzer Agent（分析文件）
       ├──→ Planner Agent（规划大纲）
       ├──→ Page Generator Agent（生成页面）
       └──→ Page Optimizer Agent（优化页面）


## LangGraph 状态定义


from typing import TypedDict, Literal

class ProjectState(TypedDict):
    project_id: str
    user_message: str
    chat_history: list[dict]
    uploaded_files: list[dict]       # 刚上传的文件信息
    parsed_contents: list[dict]      # 所有已解析的文件内容
    outline: dict | None             # PPT 大纲
    pages: dict[int, dict]           # 页码 → 页面状态
    global_theme: dict               # 全局主题配置
    current_phase: Literal[
        "chatting",       # 普通对话
        "analyzing",      # 正在分析文件
        "planning",       # 正在规划大纲
        "generating",     # 正在生成页面
        "optimizing",     # 正在优化某页
    ]
    current_page: int | None         # 当前正在操作的页码
    sse_callback: callable           # 流式推送回调


## 各 Agent 详细设计

### 1. Orchestrator Agent

输入：用户消息 + 当前项目状态
输出：路由决策（下一步调用哪个 Agent）

意图分类：
- has_new_files → File Analyzer Agent
- needs_planning → Planner Agent
- confirm_outline → Page Generator Agent
- optimize_page → Page Optimizer Agent
- general_chat → 直接回复

System Prompt 要点：
- 你是 PPT 制作助手的总调度
- 根据用户消息和项目当前状态，判断应该执行什么操作
- 如果用户上传了文件，先分析文件
- 如果文件分析完成且用户描述了需求，进入规划
- 如果用户确认了大纲，开始生成
- 如果在预览模式下收到消息，进入优化


### 2. File Analyzer Agent

输入：上传的文件列表
输出：每个文件的结构化摘要

处理流程：
1. 根据文件类型调用对应 Parser
2. 提取关键信息（数据、文字、结构）
3. 用 LLM 生成文件内容摘要
4. 将内容 embedding 存入 ChromaDB
5. 返回结构化结果

输出格式示例：
{
  "file_name": "Q1销售报表.xlsx",
  "file_type": "excel",
  "summary": "包含Q1各月营收数据...",
  "extracted_data": {
    "tables": [...],
    "key_metrics": { "total_revenue": 230000000, ... },
    "charts_data": [...]
  }
}


### 3. Planner Agent

输入：所有解析后的文件内容 + 用户需求描述 + 对话历史
输出：完整 PPT 大纲 JSON

System Prompt 要点：
- 你是一个专业的 PPT 内容策划师
- 根据材料内容和用户需求，规划 PPT 的页面结构
- 每页需要指定：页码、标题、页面类型、内容要点、推荐布局、使用的数据
- 要确保叙事逻辑通顺，有起承转合
- 页面类型包括：cover(封面), toc(目录), data(数据展示),
  comparison(对比), timeline(时间线), content(图文),
  keypoints(要点), quote(引言), thankyou(致谢) 等

输出格式：
{
  "title": "Q1季度经营汇报",
  "total_pages": 12,
  "theme_suggestion": "business-blue",
  "pages": [
    {
      "page_number": 1,
      "title": "Q1季度经营汇报",
      "type": "cover",
      "content_brief": "公司名称、汇报日期、汇报人",
      "layout": "center-title",
      "data_refs": []
    },
    {
      "page_number": 2,
      "title": "汇报提纲",
      "type": "toc",
      "content_brief": "四大板块：业绩总览、营收分析、产品数据、下季计划",
      "layout": "four-grid",
      "data_refs": []
    },
    {
      "page_number": 3,
      "title": "Q1 业绩总览",
      "type": "data",
      "content_brief": "营收2.3亿(+23%)、用户150万(+45%)、...",
      "layout": "kpi-cards-with-chart",
      "data_refs": ["Q1销售报表.xlsx:Sheet1:A1:D12"]
    },
    ...
  ]
}


### 4. Page Generator Agent

输入：单页规划信息 + 全局主题 + 相关数据 + 全局上下文
输出：完整的 Vue3 SFC 代码字符串

System Prompt 要点：
- 你是 Vue3 前端开发专家，擅长数据可视化和动画
- 根据页面规划，生成一个完整的 Vue3 SFC 组件
- 必须使用 <script setup lang="ts"> 语法
- 页面尺寸固定为 1920x1080（16:9），使用 CSS 缩放适配
- 可以使用的库：ECharts、GSAP、@vueuse/motion
- 数据直接内嵌在组件中（不需要 API 调用）
- 动画要优雅但不夸张
- 严格遵循全局主题的配色和字体
- 代码要完整可运行，不要省略任何部分

输出：纯 Vue SFC 代码，不要 markdown 包裹


### 5. Page Optimizer Agent

输入：当前页 Vue 代码 + 用户修改指令 + 该页对话历史
输出：修改后的完整 Vue3 SFC 代码

System Prompt 要点：
- 你负责根据用户反馈修改单个 PPT 页面
- 你会收到当前页的完整 Vue 代码和用户的修改要求
- 只修改用户要求的部分，保持其他部分不变
- 理解自然语言指代（"这个图表"、"标题字大一点"）
- 输出完整的修改后代码，不要给出 diff

输出：纯 Vue SFC 代码，不要 markdown 包裹


## LangGraph 工作流图


from langgraph.graph import StateGraph, END

workflow = StateGraph(ProjectState)

# 添加节点
workflow.add_node("orchestrate", orchestrator_node)
workflow.add_node("analyze_files", file_analyzer_node)
workflow.add_node("plan_outline", planner_node)
workflow.add_node("generate_pages", page_generator_node)
workflow.add_node("optimize_page", page_optimizer_node)
workflow.add_node("direct_reply", direct_reply_node)

# 设置入口
workflow.set_entry_point("orchestrate")

# 条件路由
workflow.add_conditional_edges("orchestrate", route_by_intent, {
    "analyze": "analyze_files",
    "plan": "plan_outline",
    "generate": "generate_pages",
    "optimize": "optimize_page",
    "chat": "direct_reply",
})

# 分析完文件后可能需要规划
workflow.add_conditional_edges("analyze_files", should_plan_after_analyze, {
    "plan": "plan_outline",
    "wait": END,  # 等待用户进一步指令
})

# 规划完成后等待用户确认
workflow.add_edge("plan_outline", END)

# 生成完成
workflow.add_edge("generate_pages", END)

# 优化完成
workflow.add_edge("optimize_page", END)

# 直接回复完成
workflow.add_edge("direct_reply", END)

graph = workflow.compile()



---

### `docs/04-data-model.md`


# 数据模型设计

## SQLite 表设计

### projects 表

CREATE TABLE projects (
    id TEXT PRIMARY KEY,                -- UUID
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft', -- draft/planning/generating/editing/completed/archived
    theme_config TEXT,                   -- JSON: 主题配置
    outline TEXT,                        -- JSON: PPT 大纲
    total_pages INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


### project_pages 表

CREATE TABLE project_pages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    page_number INTEGER NOT NULL,
    title TEXT,
    page_type TEXT,                       -- cover/data/comparison/...
    vue_code TEXT,                        -- 当前版本的 Vue SFC 代码
    status TEXT DEFAULT 'planned',        -- planned/generating/generated/confirmed
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, page_number)
);


### page_versions 表

CREATE TABLE page_versions (
    id TEXT PRIMARY KEY,
    page_id TEXT NOT NULL REFERENCES project_pages(id),
    version INTEGER NOT NULL,
    vue_code TEXT NOT NULL,
    change_description TEXT,              -- 本次修改的描述
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


### uploaded_files 表

CREATE TABLE uploaded_files (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    original_name TEXT NOT NULL,
    file_type TEXT NOT NULL,              -- excel/word/pdf/pptx/image/csv
    file_path TEXT NOT NULL,              -- 本地存储路径
    file_size INTEGER,
    parsed_content TEXT,                  -- JSON: 解析后的结构化内容
    parse_status TEXT DEFAULT 'pending',  -- pending/parsing/parsed/failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


### chat_messages 表

CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    page_number INTEGER,                  -- NULL=项目级对话, 有值=页面级优化对话
    role TEXT NOT NULL,                    -- user/assistant/system
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',     -- text/file_upload/outline/code/status
    metadata TEXT,                        -- JSON: 附加信息(文件ID、Agent名称等)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


### settings 表

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 存储: llm_provider, model_name, api_base_url 等（API Key 不存这里，用 Electron safeStorage）


## Pydantic Schema


from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    GENERATING = "generating"
    EDITING = "editing"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class PageStatus(str, Enum):
    PLANNED = "planned"
    GENERATING = "generating"
    GENERATED = "generated"
    OPTIMIZING = "optimizing"
    CONFIRMED = "confirmed"

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None
    status: ProjectStatus
    total_pages: int
    created_at: datetime
    updated_at: datetime

class PageResponse(BaseModel):
    id: str
    project_id: str
    page_number: int
    title: str | None
    page_type: str | None
    vue_code: str | None
    status: PageStatus
    version: int

class ChatMessageCreate(BaseModel):
    content: str
    page_number: int | None = None       # 如果是页面级优化对话

class OutlineSchema(BaseModel):
    title: str
    total_pages: int
    theme_suggestion: str
    pages: list["OutlinePageSchema"]

class OutlinePageSchema(BaseModel):
    page_number: int
    title: str
    type: str
    content_brief: str
    layout: str
    data_refs: list[str]

class SSEEvent(BaseModel):
    event: str       # thinking/outline/code_chunk/preview_ready/error/done
    data: dict



---

### `docs/05-api-design.md`


# API 接口设计

Base URL: `http://127.0.0.1:18930/api`

## 项目管理

### 获取项目列表

GET /projects
Query: ?status=editing&sort=updated_at&order=desc
Response: { projects: ProjectResponse[], total: number }


### 创建项目

POST /projects
Body: { name: string, description?: string }
Response: ProjectResponse


### 获取项目详情

GET /projects/{project_id}
Response: ProjectResponse & { pages: PageResponse[], outline?: OutlineSchema }


### 更新项目

PATCH /projects/{project_id}
Body: { name?: string, description?: string, status?: string }
Response: ProjectResponse


### 删除项目

DELETE /projects/{project_id}
Response: { success: true }


## 文件管理

### 上传文件

POST /projects/{project_id}/files
Content-Type: multipart/form-data
Body: file (binary)
Response: { file_id: string, original_name: string, file_type: string, parse_status: string }


### 获取项目文件列表

GET /projects/{project_id}/files
Response: { files: FileResponse[] }


### 获取文件解析结果

GET /projects/{project_id}/files/{file_id}/parsed
Response: { file_id: string, parsed_content: object, status: string }


## Agent 对话（核心）

### 发送消息（SSE 流式响应）

POST /projects/{project_id}/agent/chat
Content-Type: application/json
Body: {
    message: string,
    page_number?: number       // 为空=项目级对话，有值=页面级优化
}
Response: text/event-stream

SSE 事件类型:
  event: thinking
  data: { "agent": "planner", "content": "正在分析您的数据结构..." }

  event: file_parsed
  data: { "file_id": "xxx", "file_name": "sales.xlsx", "summary": "..." }

  event: outline
  data: { "outline": OutlineSchema }

  event: page_generating
  data: { "page_number": 3, "status": "generating" }

  event: code_chunk
  data: { "page_number": 3, "chunk": "<template>...", "is_complete": false }

  event: page_complete
  data: { "page_number": 3, "vue_code": "...(完整代码)" }

  event: assistant_message
  data: { "content": "已完成第3页的生成，..." }

  event: error
  data: { "message": "生成失败: ..." }

  event: done
  data: {}


### 确认大纲并开始生成

POST /projects/{project_id}/agent/confirm-outline
Body: { outline?: OutlineSchema }    // 可传入用户修改后的大纲，不传则使用当前大纲
Response: text/event-stream          // 同上，流式返回生成过程


### 重新生成某一页

POST /projects/{project_id}/pages/{page_number}/regenerate
Response: text/event-stream


## 页面管理

### 获取页面代码

GET /projects/{project_id}/pages/{page_number}
Response: PageResponse


### 获取页面历史版本

GET /projects/{project_id}/pages/{page_number}/versions
Response: { versions: PageVersionResponse[] }


### 回滚到指定版本

POST /projects/{project_id}/pages/{page_number}/rollback
Body: { version: number }
Response: PageResponse


### 调整页面顺序

PUT /projects/{project_id}/pages/reorder
Body: { page_order: number[] }    // [3, 1, 2, 4, ...] 新的页码顺序
Response: { success: true }


## 预览

### 构建单页预览

POST /projects/{project_id}/pages/{page_number}/preview
Response: { preview_url: string }    // iframe 可加载的 URL


### 获取页面缩略图

GET /projects/{project_id}/pages/{page_number}/thumbnail
Response: image/png


## 导出

### 导出为 PDF

POST /projects/{project_id}/export/pdf
Response: { task_id: string }

GET /projects/{project_id}/export/{task_id}/status
Response: { status: "processing"|"completed", download_url?: string }


## 主题

### 获取可用主题列表

GET /themes
Response: { themes: ThemeConfig[] }


### 应用主题到项目

PUT /projects/{project_id}/theme
Body: ThemeConfig
Response: { success: true }


## 设置

### 获取设置

GET /settings
Response: { llm_provider: string, model_name: string, ... }


### 更新设置

PUT /settings
Body: { llm_provider?: string, model_name?: string, ... }
Response: { success: true }


## 健康检查

GET /health
Response: { status: "ok", version: "0.1.0" }



---

### `docs/06-ui-pages.md`


# 页面设计与交互

## 路由结构


/                          → Dashboard 项目列表
/project/:id               → 重定向到对应模式
/project/:id/chat          → Workspace 对话模式（创建/规划阶段）
/project/:id/preview       → Workspace 预览模式（浏览/优化阶段）
/settings                  → 设置页


## 页面一：Dashboard

### 布局

┌──────────────────────────────────────────────────┐
│  Logo   PPT Studio                    [⚙️ 设置]  │
├──────────────────────────────────────────────────┤
│                                                  │
│  我的项目                        [+ 新建项目]     │
│                                                  │
│  筛选: [全部] [创作中] [已完成] [已归档]           │
│                                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│  │ 缩略图  │ │ 缩略图  │ │ 缩略图  │ │ 缩略图  │   │
│  │        │ │        │ │        │ │   +    │   │
│  │ 项目名  │ │ 项目名  │ │ 项目名  │ │  新建  │   │
│  │ 状态标签│ │ 状态标签│ │ 状态标签│ │        │   │
│  │ 更新时间│ │ 更新时间│ │ 更新时间│ │        │   │
│  │ [··· ] │ │ [··· ] │ │ [··· ] │ │        │   │
│  └────────┘ └────────┘ └────────┘ └────────┘   │
│                                                  │
└──────────────────────────────────────────────────┘


### 交互
- 点击项目卡片 → 进入 `/project/:id/chat` 或 `/project/:id/preview`（取决于项目状态）
- 新建项目 → 弹出对话框输入名称 → 创建后进入 `/project/:id/chat`
- 卡片右下角 `···` 菜单 → 重命名、删除、归档、复制
- 缩略图展示项目第一页的预览（如有）

## 页面二：Workspace - 对话模式

### 布局

┌──────────────────────────────────────────────────────────┐
│  ← Dashboard │ 📊 项目名称  │ 状态标签 │ [切换到预览模式] │
├──────────────────────────┬───────────────────────────────┤
│                          │                               │
│  💬 对话区域              │   📋 PPT 大纲面板              │
│  (可滚动)                │   (实时更新)                   │
│                          │                               │
│  ┌────────────────────┐  │   项目: Q1季度汇报             │
│  │ 🤖 你好！请上传资料 │  │   页数: 12页                  │
│  │   并描述你的需求    │  │   主题: 商务蓝                │
│  └────────────────────┘  │                               │
│                          │   □ 第1页: 封面               │
│  ┌────────────────────┐  │     类型: cover               │
│  │ 📎 sales.xlsx      │  │     简述: 公司名称...          │
│  │ 📎 report.pdf      │  │                               │
│  │ 👤 帮我做Q1季度汇报 │  │   □ 第2页: 目录               │
│  └────────────────────┘  │     类型: toc                 │
│                          │     简述: 四大板块...           │
│  ┌────────────────────┐  │                               │
│  │ 🤖 正在分析文件...  │  │   □ 第3页: 业绩总览           │
│  │ ✅ sales.xlsx 分析  │  │     ...                      │
│  │ ✅ report.pdf 分析  │  │                               │
│  │ 📋 已规划12页 →     │  │   ────────────────────        │
│  └────────────────────┘  │   [✅ 确认大纲，开始生成]       │
│                          │   [✏️ 我想调整...]             │
│  ┌─────────────────┬──┐  │                               │
│  │ 输入消息...      │📤│  │                               │
│  │            📎    │  │  │                               │
│  └─────────────────┴──┘  │                               │
│                          │                               │
│  📎 已上传: 2个文件       │                               │
├──────────────────────────┴───────────────────────────────┤
│                   状态栏: Agent 工作状态指示                │
└──────────────────────────────────────────────────────────┘


### 交互说明
- 左侧对话面板支持：发文字、上传文件(拖拽或点击📎)、展示Agent流式回复
- 右侧大纲面板：Agent 规划后实时出现，每个页面条目可展开看详情
- 大纲确认按钮：点击后 Agent 开始逐页生成，自动切换到预览模式
- Agent 流式回复：typing 效果逐字出现，文件分析结果卡片化展示
- 对话中的代码块、大纲引用等用特殊卡片样式渲染
- 当大纲还没有时，右侧面板显示引导状态："上传文件并描述需求后，AI 将为您规划 PPT 结构"

## 页面三：Workspace - 预览模式

### 布局

┌──────────────────────────────────────────────────────────────┐
│ ← Dashboard │ 📊 项目名称 │ [对话模式] [预览模式] │ [全屏] [导出] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │              PPT 页面预览区域                          │   │
│  │              (iframe 渲染)                            │   │
│  │              16:9 等比缩放                            │   │
│  │                                                      │   │
│  │         ◀ 上一页    3 / 12    下一页 ▶               │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌── 当前页操作区 ──────────────────────────────────────────┐ │
│  │                                                         │ │
│  │ 快捷工具: [🎨换配色] [📐换布局] [✨换动画] [🔄重新生成] [✅确认] │ │
│  │                                                         │ │
│  │ 💬 优化对话 (针对第3页):                                  │ │
│  │ ┌─────────────────────────────────────────────────────┐ │ │
│  │ │ 👤 图表改成柱状图                                    │ │ │
│  │ │ 🤖 已修改 ✅                                        │ │ │
│  │ │ 👤 数字加个滚动动画                                  │ │ │
│  │ │ 🤖 已添加数字滚动效果 ✅                             │ │ │
│  │ └─────────────────────────────────────────────────────┘ │ │
│  │ ┌───────────────────────────────────────────┐ [发送]    │ │
│  │ │ 对这一页有什么修改意见...                    │          │ │
│  │ └───────────────────────────────────────────┘          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌── 页面缩略图导航 ────────────────────────────────────────┐ │
│  │ [1🟢] [2🟢] [*3🟡*] [4⚪] [5⚪] ... [12⚪]  [+添加页] │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘


### 交互说明
- **预览区** ：iframe 渲染 Agent 生成的 Vue 页面，16:9 画布等比缩放适配容器
- **翻页** ：左右箭头键 / 点击按钮 / 点击缩略图
- **翻页时** ：对话区自动切换到对应页面的对话历史
- **快捷工具** ：预设常用修改指令，点击后自动发送给 Agent
- **对话区** ：每个页面独立的对话历史，优化指令自动携带页码
- **缩略图导航** ：底部横向滚动，颜色标识状态
  - 🟢 已确认 - 用户满意该页
  - 🟡 修改中 - 当前正在操作/Agent正在处理
  - ⚪ 待确认 - 已生成但未确认
  - ⭕ 生成中 - Agent 正在生成代码
  - 灰色 - 未生成
- **拖拽排序** ：缩略图支持拖拽调整页面顺序
- **右键菜单** ：缩略图右键 → 删除页 / 在后面插入新页 / 复制页 / 查看历史版本
- **确认按钮** ：当前页确认满意后，缩略图变绿

## 页面四：Settings

### 布局

┌──────────────────────────────────┐
│  ← 返回   ⚙️ 设置                │
├──────────────────────────────────┤
│                                  │
│  🤖 AI 模型设置                   │
│  ├── 模型提供商: [Claude ▾]      │
│  ├── 模型: [claude-sonnet ▾]     │
│  ├── API Key: [••••••••] [显示]  │
│  ├── API Base URL: [可选自定义]   │
│  └── [测试连接]                   │
│                                  │
│  🎨 默认主题                      │
│  └── [主题选择器]                 │
│                                  │
│  📁 存储位置                      │
│  └── /Users/xxx/PPTStudio [更改] │
│                                  │
│  🌐 语言: [中文 ▾]               │
│                                  │
│  ℹ️ 关于                          │
│  └── 版本 0.1.0 | 检查更新        │
│                                  │
└──────────────────────────────────┘


## 组件拆分规划


src/components/
├── common/
│   ├── AppHeader.vue              # 顶部导航栏
│   ├── StatusBadge.vue            # 状态标签
│   ├── LoadingDots.vue            # 加载动画
│   └── ConfirmDialog.vue          # 确认对话框
├── dashboard/
│   ├── ProjectCard.vue            # 项目卡片
│   ├── ProjectGrid.vue            # 项目网格
│   ├── CreateProjectDialog.vue    # 新建项目弹窗
│   └── ProjectFilter.vue         # 筛选栏
├── chat/
│   ├── ChatPanel.vue              # 对话面板容器
│   ├── ChatMessage.vue            # 单条消息
│   ├── ChatInput.vue              # 输入框+上传
│   ├── FileUploadArea.vue         # 文件上传区域
│   ├── FileCard.vue               # 已上传文件卡片
│   ├── ThinkingBubble.vue         # Agent思考中气泡
│   └── OutlineCard.vue            # 大纲展示卡片
├── outline/
│   ├── OutlinePanel.vue           # 大纲面板容器
│   ├── OutlinePageItem.vue        # 单页大纲条目
│   └── OutlineEmptyState.vue      # 空状态引导
├── preview/
│   ├── PreviewPanel.vue           # 预览面板容器
│   ├── SlideRenderer.vue          # iframe 渲染器
│   ├── SlideControls.vue          # 翻页控制
│   ├── QuickActions.vue           # 快捷操作栏
│   ├── PageOptimizeChat.vue       # 页面级优化对话
│   └── ThumbnailNav.vue           # 缩略图导航栏
│       ├── ThumbnailItem.vue      # 单个缩略图
│       └── ThumbnailContextMenu.vue
├── settings/
│   ├── LLMSettings.vue            # 模型设置
│   ├── ThemeSettings.vue          # 主题设置
│   └── StorageSettings.vue        # 存储设置
└── ppt-templates/                 # PPT 预设主题/组件
    ├── themes/
    │   ├── business-blue.ts
    │   ├── tech-dark.ts
    │   └── fresh-green.ts
    └── slide-components/          # 可在生成的PPT中使用的组件
        ├── CountUp.vue            # 数字滚动
        ├── AnimatedChart.vue      # 动画图表
        └── ProgressBar.vue        # 进度条



---

### `docs/07-ppt-render-engine.md`


# PPT 渲染引擎方案

## 核心挑战
Agent 生成的是 Vue3 SFC 源代码字符串，需要在前端实时编译并渲染为可交互的页面。

## 方案选择：iframe + 本地 Vite Dev Server

### 原理

Agent 生成 Vue SFC 代码
    ↓
Python 后端写入文件 pages/page-{n}.vue
    ↓
本地 Vite Dev Server 监听文件变更 (HMR)
    ↓
前端 iframe 加载 http://localhost:18921/slide/{n}
    ↓
文件更新时 Vite HMR 自动热刷新 iframe 内容


### 架构

python-backend/
    写入 → ppt-preview-server/src/slides/page-{n}.vue

ppt-preview-server/          # 独立的 Vite 项目（预览沙箱）
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router.ts            # /slide/1, /slide/2, ...
│   ├── slides/              # Agent 生成的代码写入此目录
│   │   ├── page-1.vue
│   │   ├── page-2.vue
│   │   └── ...
│   ├── theme/               # 主题变量
│   │   └── variables.css
│   └── components/          # 预装的可用组件
│       ├── CountUp.vue
│       ├── AnimatedChart.vue
│       └── ...
├── package.json              # 预装 echarts, gsap, @vueuse/motion
└── vite.config.ts


### 预览 Vite 项目配置

// ppt-preview-server/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 18921,
    strictPort: true,
    host: '127.0.0.1',
  },
})


### 预览路由

// ppt-preview-server/src/router.ts
import { createRouter, createWebHistory } from 'vue-router'

// 动态导入 slides 目录下的所有 .vue 文件
const slideModules = import.meta.glob('./slides/page-*.vue')

const routes = Object.entries(slideModules).map(([path, component]) => {
  const pageNumber = path.match(/page-(\d+)\.vue/)?.[1]
  return {
    path: `/slide/${pageNumber}`,
    component,
  }
})

export default createRouter({
  history: createWebHistory(),
  routes,
})


### 前端 iframe 集成

<!-- src/components/preview/SlideRenderer.vue -->
<template>
  <div class="slide-renderer" ref="containerRef">
    <iframe
      ref="iframeRef"
      :src="`http://127.0.0.1:18921/slide/${pageNumber}`"
      sandbox="allow-scripts allow-same-origin"
      :style="iframeStyle"
      @load="onIframeLoad"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useElementSize } from '@vueuse/core'

const props = defineProps<{
  pageNumber: number
}>()

const containerRef = ref<HTMLElement>()
const iframeRef = ref<HTMLIFrameElement>()
const { width: containerWidth, height: containerHeight } = useElementSize(containerRef)

// PPT 原始尺寸 1920x1080 (16:9)
const SLIDE_WIDTH = 1920
const SLIDE_HEIGHT = 1080

const iframeStyle = computed(() => {
  const scaleX = containerWidth.value / SLIDE_WIDTH
  const scaleY = containerHeight.value / SLIDE_HEIGHT
  const scale = Math.min(scaleX, scaleY)

  return {
    width: `${SLIDE_WIDTH}px`,
    height: `${SLIDE_HEIGHT}px`,
    transform: `scale(${scale})`,
    transformOrigin: 'top left',
  }
})

// 页面切换时刷新 iframe
watch(() => props.pageNumber, () => {
  if (iframeRef.value) {
    iframeRef.value.src = `http://127.0.0.1:18921/slide/${props.pageNumber}`
  }
})
</script>


### 主题注入

/* ppt-preview-server/src/theme/variables.css */
/* Python 后端在切换主题时重写此文件，触发 HMR */
:root {
  --slide-primary: #1a73e8;
  --slide-secondary: #4285f4;
  --slide-accent: #ea4335;
  --slide-bg: #ffffff;
  --slide-text: #202124;
  --slide-text-secondary: #5f6368;
  --slide-font-title: 'Inter', sans-serif;
  --slide-font-body: 'Inter', sans-serif;
}


### 缩略图生成

# python-backend/app/services/thumbnail_service.py
# 使用 Playwright 截图生成缩略图

from playwright.async_api import async_playwright

async def generate_thumbnail(page_number: int, project_id: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(f"http://127.0.0.1:18921/slide/{page_number}")
        await page.wait_for_load_state("networkidle")

        thumbnail_path = f"projects/{project_id}/thumbnails/page-{page_number}.png"
        await page.screenshot(path=thumbnail_path)
        await browser.close()
    
        return thumbnail_path


### Agent 生成代码时可用的组件和库

Agent 生成页面代码时，以下库和组件可直接 import 使用：


预装 npm 包:
- vue (Composition API)
- echarts + vue-echarts
- gsap
- @vueuse/motion
- @vueuse/core

预装自定义组件（在 components/ 目录下）:
- CountUp          数字滚动动画
- AnimatedChart    封装的动画图表
- ProgressBar      进度条
- IconCard         图标卡片
- DataTable        数据表格
- TimelineItem     时间线节点
- QuoteBlock       引用块

CSS 变量（通过 theme/variables.css 全局注入）:
- --slide-primary, --slide-secondary 等

每个 slide 组件的根元素应该是:
<div class="slide" style="width: 1920px; height: 1080px; overflow: hidden;">



---

### `docs/development-phases/phase-1-foundation.md`


# Phase 1 - 基础骨架搭建

## 目标
搭建完整的项目工程结构，实现 Electron + Vue3 + Python 三端跑通，
可以在界面上新建项目、看到项目列表，Python 后端能正常启动和通信。

## 预计工时
3-5 天

## 任务清单

### 1.1 初始化 Electron + Vue3 项目
- [ ] 使用 electron-vite 创建项目骨架
- [ ] 配置 TypeScript
- [ ] 配置 UnoCSS
- [ ] 配置 Naive UI（按需导入）
- [ ] 配置 unplugin-auto-import、unplugin-vue-components
- [ ] 配置 Vue Router
- [ ] 配置 Pinia
- [ ] 创建完整的目录结构（参照 CLAUDE.md 中定义的结构）
- [ ] 验证：`pnpm dev` 能正常启动 Electron 窗口并显示 Vue 页面

### 1.2 初始化 Python 后端
- [ ] 在 python-backend/ 下创建 pyproject.toml，使用 uv 管理依赖
- [ ] 安装核心依赖：fastapi, uvicorn, sqlalchemy, aiosqlite, pydantic, loguru, sse-starlette, python-multipart, aiofiles
- [ ] 创建 FastAPI 应用骨架（main.py）
- [ ] 实现 /health 健康检查接口
- [ ] 配置 CORS（允许 Electron 渲染进程访问）
- [ ] 创建 config.py 配置管理（数据目录、端口等）
- [ ] 配置 Loguru 日志
- [ ] 验证：`uv run fastapi dev app/main.py --port 18930` 能正常启动，访问 /health 返回 ok

### 1.3 Electron 主进程 - Python Sidecar 管理
- [ ] 实现 PythonSidecar 类（electron/sidecar/python-manager.ts）
  - start()：启动 Python 子进程
  - stop()：关闭 Python 子进程
  - waitForReady()：轮询 /health 等待就绪
  - getBaseUrl()：返回 Python 服务地址
- [ ] 在 Electron 主进程 app.whenReady() 中启动 Python Sidecar
- [ ] 在 app.before-quit 中优雅关闭 Python 进程
- [ ] 实现 IPC handler 让渲染进程获取 Python 服务地址
- [ ] 验证：启动 Electron 后 Python 后端自动启动，关闭 Electron 后 Python 自动退出

### 1.4 数据库初始化
- [ ] 使用 SQLAlchemy 2.0 定义 ORM 模型（models/）
  - Project 模型
  - ProjectPage 模型
  - PageVersion 模型
  - UploadedFile 模型
  - ChatMessage 模型
  - Setting 模型
- [ ] 创建 db/database.py 数据库连接管理（async engine + session）
- [ ] 实现数据库自动创建表逻辑（应用启动时）
- [ ] 定义 Pydantic schemas（schemas/）
- [ ] 验证：启动后自动在数据目录下生成 ppt_studio.db

### 1.5 项目 CRUD API
- [ ] 实现项目管理 API（api/projects.py）
  - GET /api/projects — 项目列表（支持 status 筛选、排序）
  - POST /api/projects — 创建项目
  - GET /api/projects/{id} — 项目详情
  - PATCH /api/projects/{id} — 更新项目
  - DELETE /api/projects/{id} — 删除项目（同时删除本地文件）
- [ ] 实现 ProjectService 业务逻辑层
- [ ] 创建项目时自动创建本地项目目录结构
- [ ] 验证：用 Swagger UI 测试所有 CRUD 接口

### 1.6 前端 - API 调用层
- [ ] 创建 services/api.ts 封装 axios/fetch 实例
  - baseURL 从 Electron IPC 获取 Python 服务地址
  - 统一错误处理
  - 请求/响应拦截器
- [ ] 创建 services/projectService.ts 项目相关 API 调用
- [ ] 创建 types/project.ts 前端类型定义
- [ ] 验证：前端能调通后端 API

### 1.7 前端 - Dashboard 页面
- [ ] 创建 layouts/MainLayout.vue 主布局（顶部导航栏）
- [ ] 创建 pages/dashboard/DashboardPage.vue
- [ ] 创建 components/dashboard/ProjectCard.vue 项目卡片
- [ ] 创建 components/dashboard/ProjectGrid.vue 项目网格
- [ ] 创建 components/dashboard/CreateProjectDialog.vue 新建项目弹窗
- [ ] 创建 components/dashboard/ProjectFilter.vue 状态筛选栏
- [ ] 创建 stores/projectStore.ts Pinia 状态管理
- [ ] 实现功能：
  - 页面加载时获取项目列表
  - 按状态筛选项目
  - 新建项目（弹窗输入名称 → 调用 API → 跳转到项目工作区）
  - 项目卡片展示：名称、状态标签、页数、更新时间
  - 项目卡片 ··· 菜单：重命名、删除（二次确认）
  - 点击项目卡片跳转到 /project/:id/chat
  - 空状态展示（没有项目时的引导页）
- [ ] 验证：能在界面上新建项目、看到项目列表、删除项目

### 1.8 前端 - Workspace 页面骨架
- [ ] 创建 pages/workspace/WorkspacePage.vue 工作区容器
- [ ] 实现对话模式/预览模式的 tab 切换（先搭骨架，内容后续阶段填充）
- [ ] 对话模式：左右分栏布局（左侧对话区占位 + 右侧大纲区占位）
- [ ] 预览模式：上中下布局（预览区占位 + 操作区占位 + 缩略图导航占位）
- [ ] 创建 stores/workspaceStore.ts 工作区状态管理
- [ ] 验证：从 Dashboard 点击项目卡片能进入工作区，看到骨架布局，能切换两种模式

### 1.9 前端 - Settings 页面
- [ ] 创建 pages/settings/SettingsPage.vue
- [ ] LLM 设置：模型提供商选择（Claude/OpenAI/自定义）、模型名称、API Key 输入
- [ ] API Key 通过 Electron IPC 调用 safeStorage 加密存储
- [ ] 存储路径配置
- [ ] 实现 Settings API（后端 GET/PUT /api/settings）
- [ ] 验证：能保存和读取设置

## Phase 1 完成标准
1. ✅ Electron 应用正常启动，自动拉起 Python 后端
2. ✅ Dashboard 页面可以新建、查看、删除项目
3. ✅ 点击项目可进入 Workspace 骨架页面
4. ✅ Settings 页面可以配置 API Key
5. ✅ 关闭应用时 Python 进程自动退出
6. ✅ 数据持久化在本地 SQLite 中


---

### `docs/development-phases/phase-2-agent-core.md`


# Phase 2 - Agent 核心系统

## 目标
实现完整的 Agent 对话工作流：用户上传文件 + 发送消息 → 文件解析 → 大纲规划 → 前端实时展示。
本阶段不涉及 Vue 代码生成和预览，聚焦 Agent 逻辑和对话交互。

## 前置条件
Phase 1 全部完成

## 预计工时
5-7 天

## 任务清单

### 2.1 文件上传系统
- [ ] 实现文件上传 API（api/files.py）
  - POST /api/projects/{id}/files — 上传文件（multipart/form-data）
  - GET /api/projects/{id}/files — 获取项目文件列表
  - DELETE /api/projects/{id}/files/{file_id} — 删除文件
- [ ] 文件存储到项目目录 uploads/ 下
- [ ] 文件类型校验（只允许 xlsx/csv/docx/pdf/pptx/png/jpg/md/json/txt）
- [ ] 文件大小限制（单文件 50MB）
- [ ] 前端实现：
  - ChatInput.vue 添加文件上传按钮（📎）
  - FileUploadArea.vue 拖拽上传区域
  - FileCard.vue 已上传文件展示卡片（文件名、类型图标、大小、解析状态）

### 2.2 文件解析器
- [ ] 定义 BaseParser 抽象基类（parsers/base.py）
  
  class ParseResult(BaseModel):
      file_type: str
      summary: str
      text_content: str           # 全文文本
      structured_data: dict       # 结构化数据(表格/大纲等)
      key_points: list[str]       # 关键要点

  class BaseParser(ABC):
      @abstractmethod
      async def parse(self, file_path: str) -> ParseResult: ...
  
- [ ] 实现 ExcelParser（parsers/excel_parser.py）
  - 读取所有 sheet
  - 提取表头和数据
  - 计算基础统计（求和、平均、最大最小）
  - 识别可能的图表数据
- [ ] 实现 CSVParser（parsers/csv_parser.py）
  - 用 pandas 读取
  - 基础统计分析
- [ ] 实现 WordParser（parsers/word_parser.py）
  - 提取文字内容，保留标题层级
  - 提取图片描述
- [ ] 实现 PDFParser（parsers/pdf_parser.py）
  - 用 PyMuPDF 提取文字
  - 保留页面结构
- [ ] 实现 PPTXParser（parsers/pptx_parser.py）
  - 提取每页的文字内容
  - 提取布局结构
- [ ] 实现 ImageParser（parsers/image_parser.py）
  - 图片基本信息（尺寸、格式）
  - 如果配置了多模态模型，调用 LLM Vision 描述图片内容
- [ ] 实现 ParserAnthropic 根据文件类型自动选择解析器
- [ ] 验证：上传各类文件能正确解析出结构化数据

### 2.3 SSE 流式推送基础设施
- [ ] 创建 SSE 管理器（services/sse_manager.py）
  
  class SSEManager:
      async def create_stream(self, project_id: str) -> AsyncGenerator
      async def send_event(self, project_id: str, event: str, data: dict)
      async def close_stream(self, project_id: str)
  
- [ ] 实现 Agent 对话 SSE 端点（api/agent.py）
  - POST /api/projects/{id}/agent/chat → text/event-stream
- [ ] 前端实现 SSE 客户端（services/sseService.ts）
  
  class AgentSSEClient {
    connect(projectId: string, message: string, pageNumber?: number): EventSource
    onThinking(callback): void
    onFileParsed(callback): void
    onOutline(callback): void
    onAssistantMessage(callback): void
    onError(callback): void
    onDone(callback): void
    disconnect(): void
  }
  
- [ ] 验证：前端发送消息后能接收到 SSE 流式事件

### 2.4 LangGraph Agent 工作流
- [ ] 安装 LangGraph、LangChain、langchain-anthropic 依赖
- [ ] 创建 LLM 初始化工具（agents/llm.py）
  - 从设置中读取 provider、model、api_key
  - 初始化对应的 ChatModel
- [ ] 定义 ProjectState TypedDict（agents/state.py）
- [ ] 实现 Orchestrator Agent（agents/orchestrator.py）
  - 意图分类 prompt
  - 根据用户消息 + 项目状态判断下一步
  - 输出路由决策
- [ ] 实现 File Analyzer Agent（agents/file_analyzer.py）
  - 调用 ParserAnthropic 解析文件
  - 用 LLM 总结文件内容，提取关键信息
  - 通过 SSE 推送每个文件的分析结果
- [ ] 实现 Planner Agent（agents/planner.py）
  - 输入：解析后的文件内容 + 用户需求 + 对话历史
  - 输出：完整 PPT 大纲 JSON
  - 通过 SSE 推送大纲
- [ ] 构建 LangGraph 工作流（agents/graph.py）
  - 定义节点：orchestrate, analyze_files, plan_outline, direct_reply
  - 定义条件路由
  - 编译 graph
- [ ] Agent Prompts 统一管理（agents/prompts/）
  - orchestrator_prompt.py
  - file_analyzer_prompt.py
  - planner_prompt.py
- [ ] 验证：发送消息 → Agent 正确路由 → 文件分析 → 大纲生成，全链路 SSE 推送

### 2.5 对话消息持久化
- [ ] 实现 ChatMessage CRUD（api/chat.py 或集成到 agent.py）
  - 用户消息入库
  - Agent 回复入库
  - 获取项目对话历史
  - 获取某页对话历史
- [ ] Agent 调用时自动从数据库加载对话历史作为上下文

### 2.6 前端 - 对话面板完整实现
- [ ] ChatPanel.vue：完整的对话面板
  - 自动滚动到底部
  - 加载历史消息
- [ ] ChatMessage.vue：消息渲染
  - 用户消息样式
  - Agent 消息样式（支持流式逐字显示）
  - 文件上传消息（展示文件卡片）
  - 文件分析结果消息（展示分析摘要卡片）
  - 大纲消息（展示可点击的大纲卡片）
  - 系统状态消息（"正在分析文件..."）
  - markdown 渲染（使用 markdown-it）
- [ ] ThinkingBubble.vue：Agent 思考中的动态指示
- [ ] ChatInput.vue：
  - 多行输入框（Shift+Enter 换行，Enter 发送）
  - 📎 按钮触发文件上传
  - 发送按钮
  - 发送中禁用输入
- [ ] 验证：完整的对话交互流程，消息实时流式显示

### 2.7 前端 - 大纲面板完整实现
- [ ] OutlinePanel.vue：大纲面板容器
  - 空状态：引导文案
  - 有大纲时：展示大纲列表
- [ ] OutlinePageItem.vue：单页大纲条目
  - 展示：页码、标题、类型标签、内容简述
  - 可展开/折叠详情
- [ ] 大纲确认操作：
  - "确认大纲，开始生成" 按钮
  - "我想调整" 按钮（聚焦到对话输入框）
- [ ] 大纲数据存入 workspaceStore
- [ ] 验证：Agent 生成大纲后右侧面板实时展示，可交互

### 2.8 集成测试
- [ ] 完整流程测试：上传 Excel + 描述需求 → 文件分析 → 大纲生成
- [ ] 完整流程测试：上传 Word + PDF → 文件分析 → 大纲生成
- [ ] 多轮对话测试：先上传文件 → 再补充需求 → 调整大纲
- [ ] 错误处理测试：无效文件、API Key 未配置、网络错误

## Phase 2 完成标准
1. ✅ 能上传 Excel/CSV/Word/PDF/PPTX/图片文件
2. ✅ Agent 能正确解析文件内容并用自然语言总结
3. ✅ Agent 能根据文件内容 + 用户需求生成合理的 PPT 大纲
4. ✅ 对话全程 SSE 流式推送，前端实时展示
5. ✅ 大纲在右侧面板实时展示
6. ✅ 对话历史持久化，重新打开项目能看到历史消息
7. ✅ 支持多轮对话调整大纲


---

### `docs/development-phases/phase-3-ppt-engine.md`


# Phase 3 - PPT 渲染引擎 + 页面生成

## 目标
实现 PPT 页面的 Vue 代码生成和实时预览。用户确认大纲后，Agent 逐页生成 Vue3 SFC 代码，
前端通过 iframe + 本地 Vite Dev Server 实时渲染预览。

## 前置条件
Phase 2 全部完成

## 预计工时
5-7 天

## 任务清单

### 3.1 PPT 预览沙箱项目初始化
- [ ] 在项目根目录创建 ppt-preview-server/ 子项目
- [ ] 初始化 Vite + Vue3 + TypeScript 项目
- [ ] 安装预装依赖：echarts, vue-echarts, gsap, @vueuse/motion, @vueuse/core
- [ ] 创建目录结构：
  
  ppt-preview-server/
  ├── src/
  │   ├── main.ts
  │   ├── App.vue
  │   ├── router.ts                # 动态路由 /slide/:n
  │   ├── slides/                  # Agent 生成的代码写入此处
  │   │   └── .gitkeep
  │   ├── theme/
  │   │   └── variables.css        # 主题 CSS 变量
  │   └── components/              # 预装可用组件
  │       ├── CountUp.vue          # 数字滚动
  │       ├── AnimatedChart.vue    # 动画图表封装
  │       ├── ProgressBar.vue      # 进度条
  │       ├── IconCard.vue         # 图标卡片
  │       ├── DataTable.vue        # 数据表格
  │       └── index.ts             # 统一导出
  ├── package.json
  ├── vite.config.ts
  └── tsconfig.json
  
- [ ] 配置 Vite：端口 18921, host 127.0.0.1
- [ ] 实现动态路由：自动扫描 slides/ 目录下的 page-*.vue 文件
- [ ] 实现全局主题注入：引入 theme/variables.css
- [ ] 全局注册预装组件
- [ ] 验证：手动放一个 page-1.vue 到 slides/ 目录，访问 http://127.0.0.1:18921/slide/1 能渲染

### 3.2 预览服务进程管理
- [ ] Electron 主进程管理预览 Vite Dev Server 的启动和停止
  - 创建 electron/sidecar/preview-server-manager.ts
  - start()：使用 child_process 启动 `npx vite` 在 ppt-preview-server/ 目录
  - stop()：关闭进程
  - waitForReady()：轮询 http://127.0.0.1:18921 等待就绪
- [ ] 在 Electron app.whenReady() 中启动（与 Python Sidecar 并行）
- [ ] 在 app.before-quit 中关闭
- [ ] Python 后端需要知道预览服务的文件路径，以便写入生成的 Vue 代码
  - 通过启动参数或配置文件传递 slides/ 目录路径
- [ ] 验证：Electron 启动后预览服务自动可用

### 3.3 预装 PPT 组件开发
- [ ] CountUp.vue - 数字滚动动画组件
  
  Props: end(目标数字), duration(时长), prefix(前缀), suffix(后缀), decimals(小数位)
  
- [ ] AnimatedChart.vue - ECharts 动画图表封装
  
  Props: option(ECharts配置), animationDelay(延时)
  自动：初次进入视口时播放动画
  
- [ ] ProgressBar.vue - 动画进度条
  
  Props: value(0-100), color, label, animated(是否动画)
  
- [ ] IconCard.vue - 图标+数字+标签卡片
  
  Props: icon(emoji/svg), value, label, trend(涨跌百分比)
  
- [ ] DataTable.vue - 数据表格
  
  Props: columns, data, striped, animated
  
- [ ] 每个组件都要遵循主题 CSS 变量
- [ ] 验证：每个组件单独可渲染

### 3.4 全局主题系统
- [ ] 定义主题配置 TypeScript 类型（前端 types/theme.ts）
- [ ] 定义主题 Pydantic Schema（后端 schemas/theme.py）
- [ ] 预设 5 个主题：
  - business-blue（商务蓝）
  - tech-dark（科技暗色）
  - fresh-green（清新绿）
  - warm-orange（温暖橙）
  - minimal-gray（极简灰）
- [ ] 每个主题定义：colors, fonts, borderRadius, animationStyle
- [ ] 主题 → CSS Variables 转换函数
- [ ] Python 后端写入 theme/variables.css 的能力
- [ ] 前端主题选择器组件
- [ ] API：PUT /api/projects/{id}/theme
- [ ] 验证：切换主题后预览页面样式立即变化（Vite HMR）

### 3.5 Page Generator Agent 实现
- [ ] 实现 Page Generator Agent（agents/page_generator.py）
- [ ] 精心设计 System Prompt（agents/prompts/page_generator_prompt.py）
  - 明确告知可用的组件列表及其 Props
  - 明确告知可用的库和 import 方式
  - 明确告知 CSS 变量名称
  - 要求生成完整可运行的 Vue SFC
  - 包含多个高质量的 few-shot 示例
  - 根据 page_type 提供对应的模板参考
- [ ] 输入构造：
  - 单页规划信息（来自大纲）
  - 该页相关的数据（从 parsed_contents 中提取）
  - 全局主题配置
  - 上下文（项目名称、总页数、当前第几页）
- [ ] 输出处理：
  - 提取纯 Vue SFC 代码（去除 markdown 包裹）
  - 基础语法校验
  - 写入 ppt-preview-server/src/slides/page-{n}.vue
  - 存入数据库 project_pages 表
  - 创建初始版本记录
- [ ] 通过 SSE 推送生成进度
- [ ] 验证：给定大纲的一页规划，能生成可渲染的 Vue 代码

### 3.6 逐页生成流程
- [ ] 实现确认大纲接口 POST /api/projects/{id}/agent/confirm-outline
- [ ] 在 LangGraph 工作流中添加 generate_pages 节点
- [ ] 逐页串行生成（避免并发导致上下文混乱）
- [ ] 每生成完一页：
  - 写入文件系统
  - 存入数据库
  - SSE 推送 page_complete 事件
  - 前端收到后可立即预览该页
- [ ] 全部生成完成后推送 done 事件
- [ ] 项目状态自动更新为 "editing"
- [ ] 验证：确认12页大纲后，Agent 逐页生成，前端能看到进度

### 3.7 前端 - 预览面板实现
- [ ] SlideRenderer.vue：iframe 渲染组件
  - iframe src 指向预览 Vite Dev Server
  - 16:9 等比缩放适配容器
  - 加载状态指示
  - 加载失败重试
- [ ] SlideControls.vue：翻页控制
  - 上一页/下一页按钮
  - 页码显示（当前页/总页数）
  - 键盘左右箭头翻页
- [ ] ThumbnailNav.vue：底部缩略图导航
  - 横向滚动的缩略图列表
  - 当前页高亮
  - 状态颜色标识（🟢🟡⚪灰色）
  - 点击缩略图跳转到对应页
  - 拖拽排序（VueDraggable Plus）
- [ ] ThumbnailItem.vue：单个缩略图
  - 展示缩略图图片（或页码占位）
  - 状态标识
  - 右键菜单（删除、插入、复制、查看版本）
- [ ] PreviewPanel.vue：预览面板容器
  - 组合 SlideRenderer + SlideControls + ThumbnailNav
  - 管理当前页码状态
- [ ] 验证：生成完页面后能在预览面板中翻页浏览

### 3.8 生成进度展示
- [ ] 在对话模式中展示生成进度：
  - 生成中的消息气泡："正在生成第 3/12 页: 业绩总览..."
  - 进度条展示
- [ ] 在预览模式中展示生成进度：
  - 缩略图颜色变化标识已完成/生成中/待生成
  - 预览区展示当前已生成的页面
- [ ] 确认大纲后自动从对话模式切换到预览模式
- [ ] 验证：生成过程中前端有清晰的进度展示

### 3.9 集成测试
- [ ] 完整流程：上传文件 → 对话 → 大纲 → 确认 → 逐页生成 → 预览浏览
- [ ] 生成的 Vue 代码能正确渲染（封面、数据页、图表页等）
- [ ] 主题切换测试
- [ ] 大量页面（15+ 页）生成稳定性测试

## Phase 3 完成标准
1. ✅ 确认大纲后 Agent 能逐页生成 Vue3 SFC 代码
2. ✅ 生成的代码能在 iframe 预览中正确渲染
3. ✅ 封面、数据展示、图表、对比、要点等多种页面类型均可生成
4. ✅ 预装组件（CountUp、AnimatedChart 等）能正确使用
5. ✅ 主题系统生效，CSS 变量驱动统一风格
6. ✅ 翻页浏览、缩略图导航正常工作
7. ✅ 拖拽排序页面顺序
8. ✅ 生成进度实时展示


---

### `docs/development-phases/phase-4-optimization.md`


# Phase 4 - 页面优化交互

## 目标
实现预览模式下用户对单页的对话式优化：用户浏览到某页，直接输入修改意见，
Agent 理解并修改该页代码，iframe 实时刷新展示修改结果。同时实现版本管理。

## 前置条件
Phase 3 全部完成

## 预计工时
4-5 天

## 任务清单

### 4.1 Page Optimizer Agent
- [ ] 实现 Page Optimizer Agent（agents/page_optimizer.py）
  - 你会收到一个完整的 Vue SFC 代码和用户的修改要求
  - 只修改用户要求的部分，严格保持其余部分不变
  - 理解自然语言指代："这个图表"、"左边的卡片"、"标题"、"背景色"
  - 理解模糊指令："好看一点"、"大气一些"、"更专业"
  - 修改后输出完整的 Vue SFC 代码，不要输出 diff
  - 可以使用所有预装组件和库
  - 必须保持主题 CSS 变量的使用

- [ ] 输入构造：
  - 当前页的完整 Vue SFC 代码
  - 用户的修改指令
  - 该页的对话历史（最近 10 轮）
  - 页面规划信息（来自大纲，作为背景）
  - 全局主题配置
- [ ] 输出处理：
  - 提取纯 Vue SFC 代码
  - 基础语法校验
  - 旧版本备份到 page_versions 表
  - 新代码写入文件 + 更新数据库
  - SSE 推送更新完成事件
- [ ] 在 LangGraph 工作流中添加 optimize_page 节点和路由
- [ ] 验证：发送 "把标题改成红色" 能精准修改标题样式

### 4.2 页面级对话 API 完善
- [ ] 优化 POST /api/projects/{id}/agent/chat 接口
  - 当 page_number 有值时，进入页面优化模式
  - 自动加载该页的 Vue 代码和页面对话历史
  - 区分项目级对话历史和页面级对话历史
- [ ] 页面对话历史独立存储（chat_messages 表 page_number 字段）
- [ ] 加载项目时同时返回每页的对话消息数量（用于前端显示）
- [ ] 验证：不同页面有独立的对话上下文

### 4.3 前端 - 页面优化对话组件
- [ ] PageOptimizeChat.vue 页面级优化对话组件
  - 展示当前页的对话历史
  - 切换页面时自动切换对话历史
  - 消息列表（复用 ChatMessage.vue）
  - 输入框（复用 ChatInput.vue 的简化版，不需要文件上传）
  - 发送消息时自动携带当前 page_number
  - Agent 回复中标记 "已修改 ✅" 的样式
  - 发送中 / Agent 处理中的加载状态
- [ ] 集成到 PreviewPanel.vue 中：
  - 预览区下方展示 PageOptimizeChat
  - 翻页时自动切换对话
- [ ] 验证：在预览页面输入优化指令，Agent 回复后 iframe 自动刷新

### 4.4 快捷操作栏
- [ ] QuickActions.vue 快捷操作组件
  - 🎨 换配色：弹出配色方案选择，选择后自动发送 "将这一页的主色调改为 {color}" 给 Agent
  - 📐 换布局：弹出布局选项（左右分栏/上下分栏/网格/居中），选择后发送对应指令
  - ✨ 换动画：弹出动画风格选项（淡入/弹跳/滑动/无），选择后发送对应指令
  - 🔄 重新生成：二次确认后，调用 POST /api/projects/{id}/pages/{n}/regenerate
  - ✅ 确认本页：将页面状态标记为 confirmed，缩略图变绿
- [ ] 快捷操作本质上是预设 prompt + 自动发送给 Agent
- [ ] 集成到 PreviewPanel.vue 中，位于预览区和对话区之间
- [ ] 验证：点击快捷按钮触发对应优化操作

### 4.5 版本管理系统
- [ ] 每次 Agent 修改页面代码时自动：
  - 将当前版本存入 page_versions 表
  - 版本号递增
  - 记录 change_description（由 Agent 生成一句话描述修改内容）
- [ ] 实现版本管理 API：
  - GET /api/projects/{id}/pages/{n}/versions — 获取版本列表
  - POST /api/projects/{id}/pages/{n}/rollback — 回滚到指定版本
    - 回滚时当前版本也先备份
    - 将目标版本的代码写入文件 + 更新数据库
- [ ] 前端版本管理：
  - 缩略图右键菜单 → "查看历史版本"
  - 版本历史弹窗/抽屉：
    - 版本列表（版本号、修改描述、时间）
    - 点击版本可在预览区预览该版本
    - "回滚到此版本" 按钮
  - 创建 VersionHistoryDrawer.vue 组件
- [ ] 验证：修改页面3次后，能看到4个版本（初始+3次修改），能回滚到任意版本

### 4.6 页面 CRUD 操作
- [ ] 删除页面：
  - 缩略图右键 → 删除
  - 二次确认
  - 删除文件 + 数据库记录
  - 后续页面页码自动调整
  - API: DELETE /api/projects/{id}/pages/{n}
- [ ] 在某页后插入新页：
  - 缩略图右键 → "在后面插入新页"
  - 弹窗让用户描述新页内容
  - 调用 Agent 生成新页
  - 后续页面页码自动调整
  - API: POST /api/projects/{id}/pages/{n}/insert-after
- [ ] 复制页面：
  - 缩略图右键 → 复制
  - 在当前页后插入副本
  - API: POST /api/projects/{id}/pages/{n}/duplicate
- [ ] 拖拽调整页面顺序：
  - ThumbnailNav 中拖拽缩略图
  - 调用 API: PUT /api/projects/{id}/pages/reorder
  - 更新数据库页码
  - 重命名文件系统中的文件
- [ ] 验证：页面增删改排序功能完整可用

### 4.7 iframe 热刷新优化
- [ ] Agent 修改代码写入文件后，Vite HMR 自动触发
- [ ] 如果 HMR 不稳定，实现手动刷新机制：
  - Python 写入文件后通过 SSE 推送 page_updated 事件
  - 前端收到事件后给 iframe src 追加时间戳参数强制刷新
- [ ] 刷新过程中展示加载状态（避免白屏闪烁）
- [ ] 优化：刷新前记录 iframe 滚动位置，刷新后恢复
- [ ] 验证：Agent 修改代码后 iframe 在 1-2 秒内刷新展示新内容

### 4.8 对话模式与预览模式的协同
- [ ] 预览模式下也能看到项目级对话入口（折叠状态）
- [ ] 预览模式下的 "回到对话模式" 能看到完整的项目对话历史
- [ ] 在对话模式下能快速切换到预览模式查看某一页
- [ ] Agent 在优化页面时的回复也出现在项目级对话中（带标签标识"优化第3页"）
- [ ] Workspace 状态管理（workspaceStore）统一管理：
  - 当前模式（chat / preview）
  - 当前预览页码
  - 各页面对话历史
  - 页面状态
- [ ] 验证：两种模式切换流畅，数据一致

### 4.9 集成测试
- [ ] 完整优化流程：预览页面 → 输入修改意见 → Agent 修改 → 预览更新
- [ ] 多轮优化测试：对同一页连续优化3次以上
- [ ] 快捷操作测试：所有快捷按钮功能正常
- [ ] 版本回滚测试：回滚后页面正确恢复
- [ ] 页面 CRUD 测试：增加、删除、复制、排序后一切正常
- [ ] 跨页面切换测试：在不同页面间切换，对话历史正确

## Phase 4 完成标准
1. ✅ 用户能针对当前预览页面发送自然语言优化指令
2. ✅ Agent 能精准理解修改意图并生成正确的修改后代码
3. ✅ 修改后 iframe 实时刷新，用户立即看到效果
4. ✅ 每页独立的对话历史，切换页面自动切换
5. ✅ 快捷操作栏功能完整（换配色/布局/动画/重生成/确认）
6. ✅ 版本管理可用（查看历史、回滚）
7. ✅ 页面增删复制排序功能正常
8. ✅ 对话模式和预览模式切换流畅


---

### `docs/development-phases/phase-5-polish.md`


# Phase 5 - 打磨与发布

## 目标
产品体验打磨、导出功能、错误处理、性能优化、打包发布。

## 前置条件
Phase 4 全部完成

## 预计工时
4-6 天

## 任务清单

### 5.1 导出功能
- [ ] PDF 导出
  - 后端安装 Playwright
  - 实现导出服务（services/export_service.py）：
    - 用 Playwright 逐页打开预览 URL
    - 设置视口 1920x1080
    - 等待页面和动画加载完成
    - 截图每一页为 PNG
    - 合并为 PDF（使用 reportlab 或 img2pdf）
  - API: POST /api/projects/{id}/export/pdf
  - 前端展示导出进度
  - 导出完成后提供下载
- [ ] HTML 导出（可选）
  - 将生成的 Vue 代码 + 预装组件 + 主题打包为独立的静态 HTML
  - 可以在浏览器中直接打开演示
  - 使用 Vite build 构建
- [ ] 图片导出
  - 单页导出为 PNG
  - 全部页面导出为 PNG 压缩包
- [ ] 验证：导出的 PDF 样式与预览一致

### 5.2 全屏演示模式
- [ ] 实现全屏演示模式（类似 PPT 放映）
  - 进入：预览页面点击 "全屏" 按钮 或 按 F5
  - 全屏展示当前页面（隐藏所有 UI，只有 PPT 内容）
  - 键盘左右箭头或鼠标点击翻页
  - 底部显示微型页码指示器
  - ESC 退出全屏
- [ ] 创建 FullscreenPresenter.vue 组件
- [ ] 使用 Fullscreen API
- [ ] 验证：全屏模式下 PPT 展示效果良好

### 5.3 缩略图生成 (真实截图)
- [ ] 后端实现缩略图服务
  - 页面生成完成后，用 Playwright 截图生成缩略图
  - 缩略图存储到 projects/{id}/thumbnails/
  - 缩略图尺寸：384x216（16:9 缩小）
  - API: GET /api/projects/{id}/pages/{n}/thumbnail
- [ ] 代码更新后自动重新生成缩略图
- [ ] 前端 ThumbnailItem 加载真实缩略图（替代占位符）
- [ ] 缩略图加载失败时 fallback 为页码占位
- [ ] Dashboard 项目卡片展示第一页缩略图
- [ ] 验证：缩略图与实际页面内容一致

### 5.4 错误处理完善
- [ ] 前端全局错误处理
  - API 请求失败的统一 toast 提示
  - SSE 连接断开的自动重连
  - iframe 加载失败的重试机制
  - Electron 进程崩溃的恢复
- [ ] Agent 错误处理
  - LLM API 调用失败：重试 3 次，失败后返回友好错误消息
  - LLM 生成的代码无法渲染：自动让 Agent 修复（重试 1 次）
  - 文件解析失败：跳过该文件，提示用户
  - API Key 无效/过期：引导用户到设置页
- [ ] Python 后端全局异常处理
  - 所有异常捕获并记录 Loguru 日志
  - 返回统一错误格式 { error: string, detail?: string }
- [ ] 前端错误边界
  - Vue errorHandler 全局捕获
  - 关键组件的 ErrorBoundary 包裹
- [ ] 验证：各种异常情况下应用不会崩溃，用户能看到有意义的错误提示

### 5.5 性能优化
- [ ] Agent 响应优化
  - LLM 响应缓存：相同输入的分析结果缓存（ChromaDB 或本地文件）
  - 文件解析结果缓存：避免重复解析
  - 大纲规划并行：文件分析完成后立即开始规划（不等用户确认分析结果）
- [ ] 前端性能优化
  - 路由懒加载
  - 大列表虚拟滚动（项目列表很多时）
  - 图片懒加载（缩略图）
  - 对话消息虚拟滚动（消息很多时）
  - SSE 消息节流（避免频繁 DOM 更新）
- [ ] iframe 渲染优化
  - 预加载相邻页面（当前页 ± 1）
  - iframe 池复用（避免频繁创建/销毁）
- [ ] 内存管理
  - Electron 主进程监控内存使用
  - 长时间未访问的项目数据从内存释放
- [ ] 验证：20+ 页 PPT 项目操作流畅，无明显卡顿

### 5.6 UI 打磨
- [ ] 加载状态
  - 应用启动 splash screen（等待 Python 后端就绪）
  - 项目列表骨架屏 (skeleton)
  - Agent 思考中的精美动画
  - 页面生成进度的动效
- [ ] 过渡动画
  - 页面路由切换过渡
  - 模式切换（对话↔预览）过渡
  - 列表项增删过渡
  - 弹窗/抽屉进出过渡
- [ ] 响应式适配
  - 窗口大小变化时布局自适应
  - 最小窗口尺寸限制
  - 面板可拖拽调整大小（对话面板 vs 大纲面板的分隔线）
- [ ] 深色模式（可选，后续迭代）
- [ ] 空状态设计
  - 无项目时的引导
  - 无消息时的提示
  - 无页面时的提示
- [ ] 键盘快捷键
  - Ctrl+N：新建项目
  - Ctrl+Enter：发送消息
  - Left/Right：翻页
  - F5：全屏演示
  - Ctrl+Z：非全局撤销，而是弹出版本回滚面板
  - ESC：退出全屏/关闭弹窗
- [ ] 验证：整体视觉和交互体验流畅专业

### 5.7 Electron 打包与发布
- [ ] electron-builder 配置
  - Windows：NSIS 安装包 (.exe)
  - macOS：DMG 安装包 (.dmg)
  - Linux：AppImage (.AppImage)
- [ ] Python 环境打包
  - 方案 A：使用 PyInstaller 将 Python 后端打包为单独的可执行文件
  - 方案 B：使用 uv 在构建时创建独立的 Python 虚拟环境，随应用分发
  - 推荐方案 B：更灵活，便于更新 Python 依赖
  - python-backend/ 整个目录 + 虚拟环境一起放入 Electron resources/ 目录
- [ ] ppt-preview-server 打包
  - 方案：打包时将 ppt-preview-server 作为资源文件嵌入
  - 运行时解压到用户数据目录，启动本地 Vite Dev Server
  - 需要在打包中包含 node_modules（或使用 esbuild 预构建）
- [ ] 自动更新配置
  - electron-updater 配置
  - 更新服务端（GitHub Releases 或自建 S3）
- [ ] 应用签名（macOS notarization, Windows code signing）
- [ ] 构建脚本
  
  # 一键构建全平台
  pnpm run build:all

  # 构建步骤：
  # 1. 构建 Vue 前端
  # 2. 打包 Python 环境
  # 3. 打包 ppt-preview-server
  # 4. electron-builder 打包
  
- [ ] 验证：打包后的应用在干净系统上能正常安装和运行

### 5.8 自动化测试补充
- [ ] 前端单元测试（Vitest）
  - stores 测试（projectStore, workspaceStore）
  - services 测试（API 调用 mock）
  - 关键组件测试（ChatInput, SlideRenderer）
- [ ] 后端单元测试（pytest）
  - 文件解析器测试（每种格式准备测试文件）
  - API 接口测试
  - Agent prompt 格式测试
- [ ] E2E 测试（Playwright）
  - 完整用户流程自动化
  - 新建项目 → 上传文件 → 对话 → 生成 → 预览 → 优化
- [ ] 测试覆盖率目标：核心模块 > 70%
- [ ] 验证：CI 全部通过

### 5.9 文档与清理
- [ ] README.md 完善
  - 项目介绍
  - 截图/GIF 演示
  - 安装使用说明
  - 开发环境搭建
  - 技术架构说明
- [ ] 代码清理
  - 移除所有 console.log / print 调试语句
  - 移除无用的注释和死代码
  - 统一代码风格（ESLint + Ruff 全量检查）
- [ ] CHANGELOG.md 初始版本

## Phase 5 完成标准
1. ✅ PDF 导出功能正常，样式与预览一致
2. ✅ 全屏演示模式流畅
3. ✅ 缩略图为真实页面截图
4. ✅ 异常情况处理完善，应用稳定不崩溃
5. ✅ 操作流畅无明显卡顿
6. ✅ UI 过渡动画和空状态设计完整
7. ✅ 能打包为可安装的桌面应用
8. ✅ 打包后在干净系统上能正常运行
9. ✅ 核心模块有测试覆盖


---

## 现在，回到最开始的问题：如何配合 Claude 开发

### 推荐的工作方式


## 第一步：创建项目和文档

1. 创建项目仓库
2. 把上面所有文档文件创建好（CLAUDE.md + docs/ 全部文件）
3. git commit

## 第二步：按 Phase 逐步推进

每个 Phase 的工作方式：

### 开启新 Phase
告诉 Claude Code：
"请阅读 docs/development-phases/phase-{n}-xxx.md，
我们现在开始这个阶段的开发。
请从任务 {n}.1 开始。"

### 逐个任务推进
每完成一个小节（如 1.1, 1.2），验证通过后：
"任务 {n}.{m} 已验证通过。请继续任务 {n}.{m+1}。"

### 遇到问题时
"任务 {n}.{m} 在 xxx 处遇到问题：{描述}。请排查并修复。"

### 完成一个 Phase 后
"请更新 CLAUDE.md 中的'当前开发阶段'为 Phase {n+1}。"
然后 git commit。

## 第三步：Phase 之间的衔接

每个 Phase 完成后，让 Claude Code 做一次 review：
"Phase {n} 已全部完成。请检查代码质量，
确认没有遗漏的任务，然后我们开始 Phase {n+1}。"


### 关键原则


1. 【分步推进】 不要一次让 Claude Code 做太多事，一个任务节（如1.1）几十行创建
2. 【及时验证】 每个任务后验证，发现问题立即修复，不要积累
3. 【文档驱动】 CLAUDE.md 是"真理之源"，每个 Phase 结束后更新
4. 【上下文提醒】 如果 Claude Code 偏离方向，指向对应的文档：
   "请参考 docs/03-agent-system.md 中的 Agent 设计"
5. 【保持聚焦】 每次对话聚焦在当前 Phase 的当前任务


---

这套文档体系的好处是：

- **Claude 能够按需阅读**：不需要一次性理解全部内容
- **CLAUDE.md 自动加载**：每次开启对话 Claude 都会先读这个文件
- **分阶段开发**：每个 Phase 独立完整，有明确的完成标准
- **可回溯**：遇到问题时能指向具体文档章节
- **可迭代**：随着开发推进，文档也可以更新完善
