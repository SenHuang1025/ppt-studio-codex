# 数据模型设计

## SQLite 表设计

### projects 表

```sql
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
```

### project_pages 表

```sql
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
```

### page_versions 表

```sql
CREATE TABLE page_versions (
    id TEXT PRIMARY KEY,
    page_id TEXT NOT NULL REFERENCES project_pages(id),
    version INTEGER NOT NULL,
    vue_code TEXT NOT NULL,
    change_description TEXT,              -- 本次修改的描述
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### uploaded_files 表

```sql
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
```

### chat_messages 表

```sql
CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    page_number INTEGER,                  -- NULL=项目级对话, 有值=页面级优化对话
    role TEXT NOT NULL,                   -- user/assistant/system
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',     -- text/file_upload/outline/code/status
    metadata TEXT,                        -- JSON: 附加信息(文件ID、Agent名称等)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### settings 表

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

存储：`llm_provider`、`model_name`、`api_base_url`、`multi_agent_deliberation_enabled` 等。API Key 不存这里，统一使用 Electron `safeStorage`。

## Pydantic Schema

```python
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


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
    page_number: int | None = None


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
    event: str       # thinking/deliberation_started/deliberation_round/outline/code_chunk/preview_ready/error/done
    data: dict
```
