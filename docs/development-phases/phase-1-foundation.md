# Phase 1 - 基础骨架搭建

## 目标
搭建完整的项目工程结构，实现 Electron + Vue3 + Python 三端跑通，
可以在界面上新建项目、看到项目列表，Python 后端能正常启动和通信。

## 预计工时
3-5 天

## 任务清单

### 1.1 初始化 Electron + Vue3 项目
- [x] 使用 `electron-vite` 创建项目骨架
- [x] 配置 TypeScript
- [x] 配置 UnoCSS
- [x] 配置 Naive UI（按需导入）
- [x] 配置 `unplugin-auto-import`、`unplugin-vue-components`
- [x] 配置 Vue Router
- [x] 配置 Pinia
- [x] 建立全局 design tokens（颜色、圆角、阴影、间距、磨砂层级、高亮色）
- [x] 在 UnoCSS 中配置轻磨砂面板、高亮描边、渐变文字等 shortcuts
- [x] 创建完整的目录结构（参照 `AGENTS.md` 中定义的结构）
- [x] 验证：`pnpm dev` 能正常启动 Electron 窗口并显示 Vue 页面

### 1.2 初始化 Python 后端
- [ ] 在 `python-backend/` 下创建 `pyproject.toml`，使用 `uv` 管理依赖
- [ ] 安装核心依赖：`fastapi`、`uvicorn`、`sqlalchemy`、`aiosqlite`、`pydantic`、`loguru`、`sse-starlette`、`python-multipart`、`aiofiles`
- [ ] 创建 FastAPI 应用骨架（`main.py`）
- [ ] 实现 `/health` 健康检查接口
- [ ] 配置 CORS（允许 Electron 渲染进程访问）
- [ ] 创建 `config.py` 配置管理（数据目录、端口等）
- [ ] 配置 Loguru 日志
- [ ] 验证：`uv run fastapi dev app/main.py --port 18922` 能正常启动，访问 `/health` 返回 `ok`

### 1.3 Electron 主进程 - Python Sidecar 管理
- [ ] 实现 `PythonSidecar` 类（`electron/sidecar/python-manager.ts`）
- [ ] `start()`：启动 Python 子进程
- [ ] `stop()`：关闭 Python 子进程
- [ ] `waitForReady()`：轮询 `/health` 等待就绪
- [ ] `getBaseUrl()`：返回 Python 服务地址
- [ ] 在 Electron 主进程 `app.whenReady()` 中启动 Python Sidecar
- [ ] 在 `app.before-quit` 中优雅关闭 Python 进程
- [ ] 实现 IPC handler 让渲染进程获取 Python 服务地址
- [ ] 验证：启动 Electron 后 Python 后端自动启动，关闭 Electron 后 Python 自动退出

### 1.4 数据库初始化
- [ ] 使用 SQLAlchemy 2.0 定义 ORM 模型（`models/`）
- [ ] Project 模型
- [ ] ProjectPage 模型
- [ ] PageVersion 模型
- [ ] UploadedFile 模型
- [ ] ChatMessage 模型
- [ ] Setting 模型
- [ ] 创建 `db/database.py` 数据库连接管理（async engine + session）
- [ ] 实现数据库自动创建表逻辑（应用启动时）
- [ ] 定义 Pydantic schemas（`schemas/`）
- [ ] 验证：启动后自动在数据目录下生成 `ppt_studio.db`

### 1.5 项目 CRUD API
- [ ] 实现项目管理 API（`api/projects.py`）
- [ ] `GET /api/projects`：项目列表（支持 `status` 筛选、排序）
- [ ] `POST /api/projects`：创建项目
- [ ] `GET /api/projects/{id}`：项目详情
- [ ] `PATCH /api/projects/{id}`：更新项目
- [ ] `DELETE /api/projects/{id}`：删除项目（同时删除本地文件）
- [ ] 实现 `ProjectService` 业务逻辑层
- [ ] 创建项目时自动创建本地项目目录结构
- [ ] 验证：用 Swagger UI 测试所有 CRUD 接口

### 1.6 前端 - API 调用层
- [ ] 创建 `services/api.ts` 封装 axios / fetch 实例
- [ ] `baseURL` 从 Electron IPC 获取 Python 服务地址
- [ ] 统一错误处理
- [ ] 请求 / 响应拦截器
- [ ] 创建 `services/projectService.ts` 项目相关 API 调用
- [ ] 创建 `types/project.ts` 前端类型定义
- [ ] 验证：前端能调通后端 API

### 1.7 前端 - Dashboard 页面
- [ ] 创建 `layouts/MainLayout.vue` 主布局（顶部导航栏）
- [ ] 创建 `pages/dashboard/DashboardPage.vue`
- [ ] 创建 `components/dashboard/ProjectCard.vue` 项目卡片
- [ ] 创建 `components/dashboard/ProjectGrid.vue` 项目网格
- [ ] 创建 `components/dashboard/CreateProjectDialog.vue` 新建项目弹窗
- [ ] 创建 `components/dashboard/ProjectFilter.vue` 状态筛选栏
- [ ] 创建 `components/common/AmbientBackground.vue` 全局暖色环境背景
- [ ] 创建 `components/common/AppDock.vue` 左侧悬浮导航坞
- [ ] 创建 `stores/projectStore.ts` Pinia 状态管理
- [ ] 实现功能：
- [ ] Dashboard 使用“欢迎区 + 最近项目网格”的焦点式布局
- [ ] 欢迎区包含主标题、主输入框 / 上传入口、主操作按钮
- [ ] 页面加载时获取项目列表
- [ ] 按状态筛选项目
- [ ] 新建项目（弹窗输入名称 → 调用 API → 跳转到项目工作区）
- [ ] 项目卡片展示：名称、状态标签、页数、更新时间
- [ ] 项目卡片 `···` 菜单：重命名、删除（二次确认）
- [ ] 点击项目卡片跳转到 `/project/:id/chat`
- [ ] 空状态展示（没有项目时的引导页）
- [ ] 验证：能在界面上新建项目、看到项目列表、删除项目

### 1.8 前端 - Workspace 页面骨架
- [ ] 创建 `pages/workspace/WorkspacePage.vue` 工作区容器
- [ ] 实现顶部滑动胶囊模式切换器（先搭骨架，内容后续阶段填充）
- [ ] 对话模式：左侧轻磨砂对话区 + 右侧高对比度大纲编辑区
- [ ] 预览模式：左侧缩略图轨道 + 中央预览画布 + 右侧单页优化侧栏
- [ ] 创建 `stores/workspaceStore.ts` 工作区状态管理
- [ ] 验证：从 Dashboard 点击项目卡片能进入工作区，看到骨架布局，能切换两种模式

### 1.9 前端 - Settings 页面
- [ ] 创建 `pages/settings/SettingsPage.vue`
- [ ] 设置页视觉采用“中心浮窗式设置工作台”，但保持独立路由 `/settings`
- [ ] LLM 设置：模型提供商选择（OpenAI / Anthropic / 自定义兼容 OpenAI）、模型名称、API Key 输入
- [ ] API Key 通过 Electron IPC 调用 `safeStorage` 加密存储
- [ ] 存储路径配置
- [ ] 实现 Settings API（后端 `GET /api/settings` 与 `PUT /api/settings`）
- [ ] 验证：能保存和读取设置

## Phase 1 完成标准
1. ✅ Electron 应用正常启动，自动拉起 Python 后端
2. ✅ Dashboard 页面可以新建、查看、删除项目
3. ✅ 点击项目可进入 Workspace 骨架页面
4. ✅ Settings 页面可以配置 API Key
5. ✅ 关闭应用时 Python 进程自动退出
6. ✅ 数据持久化在本地 SQLite 中
