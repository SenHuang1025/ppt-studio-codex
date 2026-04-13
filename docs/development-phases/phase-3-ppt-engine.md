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
- [ ] 在项目根目录创建 `ppt-preview-server/` 子项目
- [ ] 初始化 Vite + Vue3 + TypeScript 项目
- [ ] 安装预装依赖：`echarts`、`vue-echarts`、`gsap`、`@vueuse/motion`、`@vueuse/core`
- [ ] 创建目录结构：

```text
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
```

- [ ] 配置 Vite：端口 `18921`，host `127.0.0.1`
- [ ] 实现动态路由：自动扫描 `slides/` 目录下的 `page-*.vue` 文件
- [ ] 实现全局主题注入：引入 `theme/variables.css`
- [ ] 全局注册预装组件
- [ ] 验证：手动放一个 `page-1.vue` 到 `slides/` 目录，访问 `http://127.0.0.1:18921/slide/1` 能渲染

### 3.2 预览服务进程管理
- [ ] Electron 主进程管理预览 Vite Dev Server 的启动和停止
- [ ] 创建 `electron/sidecar/preview-server-manager.ts`
- [ ] `start()`：使用 `child_process` 启动 `npx vite`，工作目录为 `ppt-preview-server/`
- [ ] `stop()`：关闭进程
- [ ] `waitForReady()`：轮询 `http://127.0.0.1:18921` 等待就绪
- [ ] 在 Electron `app.whenReady()` 中启动（与 Python Sidecar 并行）
- [ ] 在 `app.before-quit` 中关闭
- [ ] Python 后端需要知道预览服务的文件路径，以便写入生成的 Vue 代码
- [ ] 通过启动参数或配置文件传递 `slides/` 目录路径
- [ ] 验证：Electron 启动后预览服务自动可用

### 3.3 预装 PPT 组件开发
- [ ] `CountUp.vue`：数字滚动动画组件
- [ ] Props：`end`、`duration`、`prefix`、`suffix`、`decimals`
- [ ] `AnimatedChart.vue`：ECharts 动画图表封装
- [ ] Props：`option`、`animationDelay`
- [ ] 自动：初次进入视口时播放动画
- [ ] `ProgressBar.vue`：动画进度条
- [ ] Props：`value`、`color`、`label`、`animated`
- [ ] `IconCard.vue`：图标 + 数字 + 标签卡片
- [ ] Props：`icon`、`value`、`label`、`trend`
- [ ] `DataTable.vue`：数据表格
- [ ] Props：`columns`、`data`、`striped`、`animated`
- [ ] 每个组件都要遵循主题 CSS 变量
- [ ] 验证：每个组件单独可渲染

### 3.4 全局主题系统
- [ ] 定义主题配置 TypeScript 类型（前端 `types/theme.ts`）
- [ ] 定义主题 Pydantic Schema（后端 `schemas/theme.py`）
- [ ] 预设 5 个主题：
- [ ] `business-blue`（商务蓝）
- [ ] `tech-dark`（科技暗色）
- [ ] `fresh-green`（清新绿）
- [ ] `warm-orange`（温暖橙）
- [ ] `minimal-gray`（极简灰）
- [ ] 每个主题定义：`colors`、`fonts`、`borderRadius`、`animationStyle`
- [ ] 主题 → CSS Variables 转换函数
- [ ] Python 后端写入 `theme/variables.css` 的能力
- [ ] 前端主题选择器组件
- [ ] API：`PUT /api/projects/{id}/theme`
- [ ] 验证：切换主题后预览页面样式立即变化（Vite HMR）

### 3.5 Page Generator Agent 实现
- [ ] 实现 Page Generator Agent（`agents/page_generator.py`）
- [ ] 精心设计 System Prompt（`agents/prompts/page_generator_prompt.py`）
- [ ] 明确告知可用的组件列表及其 Props
- [ ] 明确告知可用的库和 import 方式
- [ ] 明确告知 CSS 变量名称
- [ ] 要求生成完整可运行的 Vue SFC
- [ ] 包含多个高质量的 few-shot 示例
- [ ] 根据 `page_type` 提供对应的模板参考
- [ ] 输入构造：
- [ ] 单页规划信息（来自大纲）
- [ ] 该页相关的数据（从 `parsed_contents` 中提取）
- [ ] 全局主题配置
- [ ] 上下文（项目名称、总页数、当前第几页）
- [ ] 输出处理：
- [ ] 提取纯 Vue SFC 代码（去除 markdown 包裹）
- [ ] 基础语法校验
- [ ] 写入 `ppt-preview-server/src/slides/page-{n}.vue`
- [ ] 存入数据库 `project_pages` 表
- [ ] 创建初始版本记录
- [ ] 当多智能体思辨模式开启时，为 Page Generator 接入 Draft → Critic / Reviewer → Synthesis 子流程
- [ ] 思辨重点：布局合理性、信息密度、主题一致性、组件可执行性
- [ ] 失败或超时后回退到单智能体生成结果
- [ ] 通过 SSE 推送生成进度
- [ ] 验证：给定大纲的一页规划，能生成可渲染的 Vue 代码

### 3.6 逐页生成流程
- [ ] 实现确认大纲接口 `POST /api/projects/{id}/agent/confirm-outline`
- [ ] 在 LangGraph 工作流中添加 `generate_pages` 节点
- [ ] 逐页串行生成（避免并发导致上下文混乱）
- [ ] 每生成完一页：
- [ ] 写入文件系统
- [ ] 存入数据库
- [ ] SSE 推送 `page_complete` 事件
- [ ] 前端收到后可立即预览该页
- [ ] 全部生成完成后推送 `done` 事件
- [ ] 项目状态自动更新为 `editing`
- [ ] 验证：确认 12 页大纲后，Agent 逐页生成，前端能看到进度

### 3.7 前端 - 预览面板实现
- [ ] `SlideRenderer.vue`：iframe 渲染组件
- [ ] iframe `src` 指向预览 Vite Dev Server
- [ ] `16:9` 等比缩放适配容器
- [ ] 加载状态指示
- [ ] 加载失败重试
- [ ] `SlideControls.vue`：翻页控制
- [ ] 上一页 / 下一页按钮
- [ ] 页码显示（当前页 / 总页数）
- [ ] 键盘左右箭头翻页
- [ ] `ThumbnailNav.vue`：左侧缩略图轨道
- [ ] 纵向滚动的缩略图列表
- [ ] 当前页高亮
- [ ] 状态颜色标识（🟢🟡⚪灰色）
- [ ] 点击缩略图跳转到对应页
- [ ] 拖拽排序（`VueDraggable Plus`）
- [ ] `ThumbnailItem.vue`：单个缩略图
- [ ] 展示缩略图图片（或页码占位）
- [ ] 状态标识
- [ ] 右键菜单（删除、插入、复制、查看版本）
- [ ] `PreviewPanel.vue`：预览面板容器
- [ ] 组合 `ThumbnailNav` + `SlideRenderer` + `SlideControls` + 右侧优化区
- [ ] 管理当前页码状态
- [ ] 验证：生成完页面后能在预览面板中翻页浏览

### 3.8 生成进度展示
- [ ] 在对话模式中展示生成进度：
- [ ] 生成中的消息气泡：“正在生成第 3/12 页：业绩总览...”
- [ ] 细线流光进度条展示
- [ ] 若开启思辨模式，展示当前页“生成草案 / 评审中 / 综合输出中”的阶段状态
- [ ] 在预览模式中展示生成进度：
- [ ] 缩略图颜色和发光状态标识已完成 / 生成中 / 待生成
- [ ] 预览区展示当前已生成的页面
- [ ] 确认大纲后自动从对话模式切换到预览模式
- [ ] 验证：生成过程中前端有清晰的进度展示

### 3.9 集成测试
- [ ] 完整流程：上传文件 → 对话 → 大纲 → 确认 → 逐页生成 → 预览浏览
- [ ] 生成的 Vue 代码能正确渲染（封面、数据页、图表页等）
- [ ] 多智能体思辨模式下的页面生成质量与耗时测试
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
9. ✅ 开启多智能体思辨模式时，页面生成流程可稳定回退与展示阶段状态
