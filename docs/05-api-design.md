# API 接口设计

Base URL: `http://127.0.0.1:18922/api`

## 项目管理

### 获取项目列表

```text
GET /projects
Query: ?status=editing&sort=updated_at&order=desc
Response: { projects: ProjectResponse[], total: number }
```

### 创建项目

```text
POST /projects
Body: { name: string, description?: string }
Response: ProjectResponse
```

### 获取项目详情

```text
GET /projects/{project_id}
Response: ProjectResponse & { pages: PageResponse[], outline?: OutlineSchema }
```

### 更新项目

```text
PATCH /projects/{project_id}
Body: { name?: string, description?: string, status?: string }
Response: ProjectResponse
```

### 删除项目

```text
DELETE /projects/{project_id}
Response: { success: true }
```

## 文件管理

### 上传文件

```text
POST /projects/{project_id}/files
Content-Type: multipart/form-data
Body: file (binary)
Response: { file_id: string, original_name: string, file_type: string, parse_status: string }
```

### 获取项目文件列表

```text
GET /projects/{project_id}/files
Response: { files: FileResponse[] }
```

### 获取文件解析结果

```text
GET /projects/{project_id}/files/{file_id}/parsed
Response: { file_id: string, parsed_content: object, status: string }
```

## Agent 对话（核心）

### 发送消息（SSE 流式响应）

```text
POST /projects/{project_id}/agent/chat
Content-Type: application/json
Body: {
    message: string,
    page_number?: number
}
Response: text/event-stream
```

SSE 事件类型：

```text
event: thinking
data: { "agent": "planner", "content": "正在分析您的数据结构..." }

event: deliberation_started
data: { "target": "planner", "rounds": 2 }

event: deliberation_round
data: { "target": "planner", "role": "critic", "content": "..." }

event: deliberation_summary
data: { "target": "planner", "summary": "..." }

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
```

### 确认大纲并开始生成

```text
POST /projects/{project_id}/agent/confirm-outline
Body: { outline?: OutlineSchema }
Response: text/event-stream
```

### 重新生成某一页

```text
POST /projects/{project_id}/pages/{page_number}/regenerate
Response: text/event-stream
```

## 页面管理

### 获取页面代码

```text
GET /projects/{project_id}/pages/{page_number}
Response: PageResponse
```

### 获取页面历史版本

```text
GET /projects/{project_id}/pages/{page_number}/versions
Response: { versions: PageVersionResponse[] }
```

### 回滚到指定版本

```text
POST /projects/{project_id}/pages/{page_number}/rollback
Body: { version: number }
Response: PageResponse
```

### 调整页面顺序

```text
PUT /projects/{project_id}/pages/reorder
Body: { page_order: number[] }
Response: { success: true }
```

## 预览

### 构建单页预览

```text
POST /projects/{project_id}/pages/{page_number}/preview
Response: { preview_url: string }
```

### 获取页面缩略图

```text
GET /projects/{project_id}/pages/{page_number}/thumbnail
Response: image/png
```

## 导出

### 导出为 PDF

```text
POST /projects/{project_id}/export/pdf
Response: { task_id: string }

GET /projects/{project_id}/export/{task_id}/status
Response: { status: "processing" | "completed", download_url?: string }
```

## 主题

### 获取可用主题列表

```text
GET /themes
Response: { themes: ThemeConfig[] }
```

### 应用主题到项目

```text
PUT /projects/{project_id}/theme
Body: ThemeConfig
Response: { success: true }
```

## 设置

### 获取设置

```text
GET /settings
Response: {
  llm_provider: string,
  model_name: string,
  api_base_url?: string,
  multi_agent_deliberation_enabled: boolean,
  ...
}
```

说明：`multi_agent_deliberation_enabled` 作为 Phase 2 对现有 Settings API 的增量扩展接入，不要求回改已完成的 Phase 1 基础设置能力。

### 更新设置

```text
PUT /settings
Body: {
  llm_provider?: string,
  model_name?: string,
  api_base_url?: string,
  multi_agent_deliberation_enabled?: boolean,
  ...
}
Response: { success: true }
```

## 健康检查

```text
GET /health
Response: { status: "ok", version: "0.1.0" }
```
