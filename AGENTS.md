# AGENTS.md - PPT Studio 项目指南

## 项目简介
PPT Studio 是一个基于 AI Agent 的 PPT 生成桌面应用。
用户通过对话 + 上传文件的方式，由 AI Agent 自动生成 Vue3 组件代码作为 PPT 页面。
技术栈：Electron + Vue3 + TypeScript + FastAPI + Python + LangGraph。

## 使用方式
- Codex 开始开发前先阅读 `docs/00-project-overview.md` 了解全貌。
- 进入具体任务前，优先阅读对应的阶段文档和相关设计文档。
  - 一次只推进一个任务节，如 `1.1`、`2.4`，避免跨阶段并行实现。
- 如果实现与文档冲突，以 `docs/` 中编号文档为准。
- 与 Codex 的协作方式见 `docs/08-codex-collaboration.md`。

## 项目文档
- 项目总览：`docs/00-project-overview.md`
- 架构设计：`docs/01-architecture.md`
- 技术选型：`docs/02-tech-stack.md`
- Agent 系统：`docs/03-agent-system.md`
- 数据模型：`docs/04-data-model.md`
- API 设计：`docs/05-api-design.md`
- 页面与交互：`docs/06-ui-pages.md`
- PPT 渲染引擎：`docs/07-ppt-render-engine.md`
- Codex 协作方式：`docs/08-codex-collaboration.md`
- 分阶段开发计划：`docs/development-phases/`

## 项目结构

```text
ppt-studio-codex/
├── AGENTS.md
├── docs/
│   ├── 00-project-overview.md
│   ├── 01-architecture.md
│   ├── 02-tech-stack.md
│   ├── 03-agent-system.md
│   ├── 04-data-model.md
│   ├── 05-api-design.md
│   ├── 06-ui-pages.md
│   ├── 07-ppt-render-engine.md
│   ├── 08-codex-collaboration.md
│   └── development-phases/
├── electron/
│   ├── main.ts
│   ├── preload.ts
│   └── sidecar/
│       ├── python-manager.ts
│       └── preview-server-manager.ts
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── common/
│   │   ├── dashboard/
│   │   ├── chat/
│   │   ├── outline/
│   │   ├── preview/
│   │   └── settings/
│   ├── composables/
│   ├── layouts/
│   ├── pages/
│   │   ├── dashboard/
│   │   ├── workspace/
│   │   └── settings/
│   ├── stores/
│   ├── services/
│   ├── types/
│   ├── utils/
│   ├── router/
│   ├── App.vue
│   └── main.ts
├── python-backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── agents/
│   │   │   └── prompts/
│   │   ├── services/
│   │   ├── parsers/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── db/
│   │   └── config.py
│   ├── pyproject.toml
│   └── README.md
├── ppt-preview-server/
│   ├── src/
│   │   ├── slides/
│   │   ├── theme/
│   │   └── components/
│   ├── package.json
│   └── vite.config.ts
├── resources/
├── package.json
├── electron.vite.config.ts
├── tsconfig.json
└── uno.config.ts
```

## 开发规范

### 前端
- 使用 Vue3 Composition API + `<script setup>` 语法。
- 组件文件名使用 PascalCase：`ProjectCard.vue`。
- 组合式函数以 `use` 开头：`useProject.ts`。
- 使用 Naive UI 组件库，不要混用其他 UI 库。
- CSS 优先使用 UnoCSS 原子类，复杂样式用 `<style scoped>`。
- 所有变量和函数必须有 TypeScript 类型。
- 已选定的应用视觉方向为“暖色、自然、纸感、轻质感工作台”。
- 应用外层壳体可以使用暖色渐层、轻磨砂面板和克制环境层次，但大纲编辑区、设置表单主体、PPT 预览画布内部必须保持高对比度实色背景。
- 磨砂、高亮、阴影、圆角、间距统一收敛为 design tokens 与 UnoCSS shortcuts，不要在组件中散落重复样式。
- `backdrop-filter` 叠加层数控制在 3 层以内；动画优先使用 `opacity`、`transform`，避免高成本滤镜动画贯穿全局。

### 后端
- 使用 async/await 异步编程。
- API 路由按功能模块划分文件。
- 所有接口入参/出参使用 Pydantic Schema 定义。
- Agent Prompt 统一放在 `agents/prompts/` 目录。
- 文件解析器实现统一的 `BaseParser` 接口。
- 使用 Loguru 记录日志。

### Agent / LLM
- 模型提供商通过设置页配置，默认走 OpenAI 兼容接口。
- 保留 Anthropic 等其他提供商的可扩展性，通过 LiteLLM 统一接入。
- 支持可选的“多智能体思辨模式”，默认关闭；优先用于提升大纲规划质量，后续再扩展到页面生成和页面优化。
- 所有 Agent 流式输出统一走 SSE 事件模型。
- 生成页面和优化页面时，必须输出完整 Vue SFC，不输出 diff。

### Git 提交规范
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `refactor`: 重构
- `style`: 样式
- `chore`: 构建 / 工具

## 常用命令

```bash
# 前端开发
pnpm dev
pnpm build

# Python 后端
cd python-backend
uv run fastapi dev app/main.py --port 18922

# 代码检查
pnpm lint
cd python-backend && uv run ruff check .
```

## 当前开发阶段
Phase 5 - 打磨与收尾

详见 `docs/development-phases/phase-5-polish.md`
