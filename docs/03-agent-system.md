# Agent 系统设计

## Agent 架构

```text
用户消息
    ↓
┌──────────────────────────────────────┐
│   Orchestrator Agent                 │
│   职责：意图识别、任务路由             │
│   模型：可配置（默认 OpenAI GPT 系列） │
└──────────┬───────────────────────────┘
           │ 根据意图路由到对应 Agent
           ├──→ File Analyzer Agent（分析文件）
           ├──→ Planner Agent（规划大纲）
           ├──→ Page Generator Agent（生成页面）
           └──→ Page Optimizer Agent（优化页面）
           
可选思辨层（默认关闭）：
目标 Agent Draft
    ↓
Critic / Reviewer
    ↓
Synthesizer
    ↓
最终输出
```

## LangGraph 状态定义

```python
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
    deliberation_enabled: bool       # 是否开启多智能体思辨模式
    deliberation_target: str | None  # 当前思辨目标: planner/generator/optimizer
    deliberation_trace: list[dict]   # 思辨过程记录
    sse_callback: callable           # 流式推送回调
```

## 各 Agent 详细设计

### 1. Orchestrator Agent

输入：用户消息 + 当前项目状态  
输出：路由决策（下一步调用哪个 Agent）

意图分类：
- `has_new_files` → File Analyzer Agent
- `needs_planning` → Planner Agent
- `confirm_outline` → Page Generator Agent
- `optimize_page` → Page Optimizer Agent
- `general_chat` → 直接回复

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

```json
{
  "file_name": "Q1销售报表.xlsx",
  "file_type": "excel",
  "summary": "包含Q1各月营收数据...",
  "extracted_data": {
    "tables": [],
    "key_metrics": {
      "total_revenue": 230000000
    },
    "charts_data": []
  }
}
```

### 3. Planner Agent

输入：所有解析后的文件内容 + 用户需求描述 + 对话历史  
输出：完整 PPT 大纲 JSON

System Prompt 要点：
- 你是一个专业的 PPT 内容策划师
- 根据材料内容和用户需求，规划 PPT 的页面结构
- 每页需要指定：页码、标题、页面类型、内容要点、推荐布局、使用的数据
- 要确保叙事逻辑通顺，有起承转合
- 页面类型包括：`cover`、`toc`、`data`、`comparison`、`timeline`、`content`、`keypoints`、`quote`、`thankyou`

输出格式：

```json
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
    }
  ]
}
```

### 4. Page Generator Agent

输入：单页规划信息 + 全局主题 + 相关数据 + 全局上下文  
输出：完整的 Vue3 SFC 代码字符串

System Prompt 要点：
- 你是 Vue3 前端开发专家，擅长数据可视化和动画
- 根据页面规划，生成一个完整的 Vue3 SFC 组件
- 必须使用 `<script setup lang="ts">` 语法
- 页面尺寸固定为 `1920x1080`（16:9），使用 CSS 缩放适配
- 可以使用的库：ECharts、GSAP、`@vueuse/motion`
- 数据直接内嵌在组件中，不需要 API 调用
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
- 理解自然语言指代，如“这个图表”“标题字大一点”
- 输出完整的修改后代码，不要给出 diff

输出：纯 Vue SFC 代码，不要 markdown 包裹

### 6. 多智能体思辨模式（可选）

目标：
- 在不改变默认单智能体主路径的前提下，为关键高价值任务增加一层“草案 → 质疑 → 综合”的增强推理流程
- 默认关闭，由设置项控制
- Phase 2 先对 Planner Agent 生效，Phase 3 扩展到 Page Generator，Phase 4 扩展到 Page Optimizer

推荐思辨流程：
1. **Draft**：目标 Agent 先给出第一版结果
2. **Critic / Reviewer**：从逻辑完整性、叙事结构、事实一致性、页面可执行性等角度提出批评和修正建议
3. **Synthesis**：综合 Draft 与 Reviewer 意见，输出最终版本

适用范围：
- `Planner Agent`：优先启用，提升大纲结构质量
- `Page Generator Agent`：可选启用，提升页面布局与信息密度平衡
- `Page Optimizer Agent`：可选启用，提升复杂修改指令下的稳定性
- `File Analyzer Agent`：默认不启用，避免在基础解析阶段引入不必要延迟和成本

SSE 可视化建议：
- `deliberation_started`
- `deliberation_round`
- `deliberation_summary`

降级策略：
- 当开关关闭时，继续使用当前单智能体路径
- 当思辨子流程失败或超时，回退到 Draft 结果，并向前端发出状态说明

## LangGraph 工作流图

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(ProjectState)

# 添加节点
workflow.add_node("orchestrate", orchestrator_node)
workflow.add_node("analyze_files", file_analyzer_node)
workflow.add_node("plan_outline", planner_node)
workflow.add_node("deliberate_plan", deliberate_plan_node)
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

# 如果开启思辨模式，规划节点先进入思辨子流程
workflow.add_conditional_edges("plan_outline", should_deliberate_plan, {
    "deliberate": "deliberate_plan",
    "finish": END,
})

# 分析完文件后可能需要规划
workflow.add_conditional_edges("analyze_files", should_plan_after_analyze, {
    "plan": "plan_outline",
    "wait": END,
})

# 思辨完成后等待用户确认
workflow.add_edge("deliberate_plan", END)

# 生成完成
workflow.add_edge("generate_pages", END)

# 优化完成
workflow.add_edge("optimize_page", END)

# 直接回复完成
workflow.add_edge("direct_reply", END)

graph = workflow.compile()
```
