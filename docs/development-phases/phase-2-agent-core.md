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
- [ ] 实现文件上传 API（`api/files.py`）
- [ ] `POST /api/projects/{id}/files`：上传文件（`multipart/form-data`）
- [ ] `GET /api/projects/{id}/files`：获取项目文件列表
- [ ] `DELETE /api/projects/{id}/files/{file_id}`：删除文件
- [ ] 文件存储到项目目录 `uploads/` 下
- [ ] 文件类型校验（只允许 `xlsx/csv/docx/pdf/pptx/png/jpg/md/json/txt`）
- [ ] 文件大小限制（单文件 50MB）
- [ ] 前端实现：
- [ ] `ChatInput.vue` 添加文件上传按钮（`📎`）
- [ ] `FileUploadArea.vue` 拖拽上传区域
- [ ] `FileCard.vue` 已上传文件展示卡片（文件名、类型图标、大小、解析状态）

### 2.2 文件解析器
- [ ] 定义 `BaseParser` 抽象基类（`parsers/base.py`）

```python
class ParseResult(BaseModel):
    file_type: str
    summary: str
    text_content: str           # 全文文本
    structured_data: dict       # 结构化数据（表格 / 大纲等）
    key_points: list[str]       # 关键要点


class BaseParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str) -> ParseResult: ...
```

- [ ] 实现 `ExcelParser`（`parsers/excel_parser.py`）
- [ ] 读取所有 sheet
- [ ] 提取表头和数据
- [ ] 计算基础统计（求和、平均、最大最小）
- [ ] 识别可能的图表数据
- [ ] 实现 `CSVParser`（`parsers/csv_parser.py`）
- [ ] 用 pandas 读取
- [ ] 基础统计分析
- [ ] 实现 `WordParser`（`parsers/word_parser.py`）
- [ ] 提取文字内容，保留标题层级
- [ ] 提取图片描述
- [ ] 实现 `PDFParser`（`parsers/pdf_parser.py`）
- [ ] 用 PyMuPDF 提取文字
- [ ] 保留页面结构
- [ ] 实现 `PPTXParser`（`parsers/pptx_parser.py`）
- [ ] 提取每页的文字内容
- [ ] 提取布局结构
- [ ] 实现 `ImageParser`（`parsers/image_parser.py`）
- [ ] 图片基本信息（尺寸、格式）
- [ ] 如果配置了多模态模型，调用 LLM Vision 描述图片内容
- [ ] 实现 `ParserRegistry`，根据文件类型自动选择解析器
- [ ] 验证：上传各类文件能正确解析出结构化数据

### 2.3 SSE 流式推送基础设施
- [ ] 创建 SSE 管理器（`services/sse_manager.py`）

```python
class SSEManager:
    async def create_stream(self, project_id: str) -> AsyncGenerator: ...
    async def send_event(self, project_id: str, event: str, data: dict): ...
    async def close_stream(self, project_id: str): ...
```

- [ ] 实现 Agent 对话 SSE 端点（`api/agent.py`）
- [ ] `POST /api/projects/{id}/agent/chat` → `text/event-stream`
- [ ] 前端实现 SSE 客户端（`services/sseService.ts`）

```ts
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
```

- [ ] 验证：前端发送消息后能接收到 SSE 流式事件

### 2.4 LangGraph Agent 工作流
- [ ] 安装 `LangGraph`、`LangChain`、`langchain-openai`、`litellm` 依赖
- [ ] 如需 Anthropic 支持，再补充 `langchain-anthropic`
- [ ] 创建 LLM 初始化工具（`agents/llm.py`）
- [ ] 从设置中读取 `provider`、`model`、`api_key`
- [ ] 初始化对应的 ChatModel
- [ ] 定义 `ProjectState` TypedDict（`agents/state.py`）
- [ ] 实现 Orchestrator Agent（`agents/orchestrator.py`）
- [ ] 意图分类 prompt
- [ ] 根据用户消息 + 项目状态判断下一步
- [ ] 输出路由决策
- [ ] 实现 File Analyzer Agent（`agents/file_analyzer.py`）
- [ ] 调用 `ParserRegistry` 解析文件
- [ ] 用 LLM 总结文件内容，提取关键信息
- [ ] 通过 SSE 推送每个文件的分析结果
- [ ] 实现 Planner Agent（`agents/planner.py`）
- [ ] 输入：解析后的文件内容 + 用户需求 + 对话历史
- [ ] 输出：完整 PPT 大纲 JSON
- [ ] 通过 SSE 推送大纲
- [ ] 构建 LangGraph 工作流（`agents/graph.py`）
- [ ] 定义节点：`orchestrate`、`analyze_files`、`plan_outline`、`direct_reply`
- [ ] 定义条件路由
- [ ] 编译 graph
- [ ] Agent Prompts 统一管理（`agents/prompts/`）
- [ ] `orchestrator_prompt.py`
- [ ] `file_analyzer_prompt.py`
- [ ] `planner_prompt.py`
- [ ] 为 Planner Agent 建立“多智能体思辨模式”基础框架（默认关闭）
- [ ] 思辨模式由设置项 `multi_agent_deliberation_enabled` 控制
- [ ] 规划节点支持 Draft → Critic / Reviewer → Synthesis 子流程
- [ ] 子流程失败或超时后回退到单智能体 Draft 结果
- [ ] 验证：发送消息 → Agent 正确路由 → 文件分析 → 大纲生成，全链路 SSE 推送

### 2.5 对话消息持久化
- [ ] 实现 ChatMessage CRUD（`api/chat.py` 或集成到 `agent.py`）
- [ ] 用户消息入库
- [ ] Agent 回复入库
- [ ] 获取项目对话历史
- [ ] 获取某页对话历史
- [ ] Agent 调用时自动从数据库加载对话历史作为上下文

### 2.6 前端 - 对话面板完整实现
- [ ] `ChatPanel.vue`：完整的对话面板
- [ ] 自动滚动到底部
- [ ] 加载历史消息
- [ ] `ChatMessage.vue`：消息渲染
- [ ] 用户消息样式
- [ ] Agent 消息样式（支持流式逐字显示）
- [ ] 思辨过程消息样式（如草案 / 评审 / 综合总结）
- [ ] 文件上传消息（展示文件卡片）
- [ ] 文件分析结果消息（展示分析摘要卡片）
- [ ] 大纲消息（展示可点击的大纲卡片）
- [ ] 系统状态消息（“正在分析文件...”）
- [ ] markdown 渲染（使用 `markdown-it`）
- [ ] `ThinkingBubble.vue`：Agent 思考中的动态指示
- [ ] `ChatInput.vue`
- [ ] 多行输入框（Shift+Enter 换行，Enter 发送）
- [ ] `📎` 按钮触发文件上传
- [ ] 发送按钮
- [ ] 发送中禁用输入
- [ ] 验证：完整的对话交互流程，消息实时流式显示

### 2.7 前端 - 大纲面板完整实现
- [ ] `OutlinePanel.vue`：大纲面板容器
- [ ] 空状态：引导文案
- [ ] 有大纲时：展示大纲列表
- [ ] `OutlinePageItem.vue`：单页大纲条目
- [ ] 展示：页码、标题、类型标签、内容简述
- [ ] 可展开 / 折叠详情
- [ ] 大纲确认操作：
- [ ] “确认大纲，开始生成” 按钮
- [ ] “我想调整” 按钮（聚焦到对话输入框）
- [ ] 大纲数据存入 `workspaceStore`
- [ ] 验证：Agent 生成大纲后右侧面板实时展示，可交互

### 2.8 多智能体思辨模式设置与可视化
- [ ] 在现有 Settings 页面基础上扩展“多智能体思辨模式”开关
- [ ] Settings API 支持读写 `multi_agent_deliberation_enabled`
- [ ] 对话 SSE 事件扩展：
- [ ] `deliberation_started`
- [ ] `deliberation_round`
- [ ] `deliberation_summary`
- [ ] 前端在对话面板中展示思辨过程，但默认折叠详细内容
- [ ] 首期只对 Planner Agent 生效，不影响 File Analyzer 默认路径
- [ ] 验证：打开开关后，生成大纲前能看到思辨过程；关闭后回到单智能体路径

### 2.9 集成测试
- [ ] 完整流程测试：上传 Excel + 描述需求 → 文件分析 → 大纲生成
- [ ] 完整流程测试：上传 Word + PDF → 文件分析 → 大纲生成
- [ ] 多轮对话测试：先上传文件 → 再补充需求 → 调整大纲
- [ ] 多智能体思辨模式测试：开启 / 关闭两种模式下均能稳定生成大纲
- [ ] 错误处理测试：无效文件、API Key 未配置、网络错误

## Phase 2 完成标准
1. ✅ 能上传 Excel / CSV / Word / PDF / PPTX / 图片文件
2. ✅ Agent 能正确解析文件内容并用自然语言总结
3. ✅ Agent 能根据文件内容 + 用户需求生成合理的 PPT 大纲
4. ✅ 对话全程 SSE 流式推送，前端实时展示
5. ✅ 大纲在右侧面板实时展示
6. ✅ 对话历史持久化，重新打开项目能看到历史消息
7. ✅ 支持多轮对话调整大纲
8. ✅ 多智能体思辨模式可开关，并已对大纲规划生效
