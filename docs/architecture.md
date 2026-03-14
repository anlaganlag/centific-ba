# 系统架构文档

**生成日期:** 2026-03-14

---

## 架构概览

BA Toolkit 采用前后端分离的三层架构，集成多个 AI 服务实现智能业务分析。

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Pages    │  │Components│  │  Stores  │  │   API    │       │
│  │ (Routes) │  │   (UI)   │  │ (Zustand)│  │ Client   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                              │
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Backend (FastAPI)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Auth   │  │   API    │  │ Services │  │  Agents  │       │
│  │  (JWT)   │  │  Routes  │  │(Business)│  │   (AI)   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│  SQLite   │  │ ChromaDB  │  │  Azure    │  │  Docling  │
│  (Data)   │  │ (Vectors) │  │  OpenAI   │  │  Serve    │
└───────────┘  └───────────┘  └───────────┘  └───────────┘
```

---

## 核心组件

### 1. Frontend Layer

| 模块 | 技术栈 | 职责 |
|------|--------|------|
| Pages | React Router | 路由和页面级组件 |
| Components | React + TailwindCSS | 可复用 UI 组件 |
| Stores | Zustand | 全局状态管理 |
| API Client | Axios | HTTP 请求和 JWT 刷新 |

**关键设计决策：**
- 使用 Zustand 而非 Redux/Context，简化状态管理
- JWT 自动刷新在 axios interceptor 中实现
- TailwindCSS 提供原子化 CSS，无需维护样式文件

### 2. Backend Layer

#### API Routes (`app/api/routes/`)

| 路由模块 | 端点前缀 | 职责 |
|----------|----------|------|
| auth.py | /api/auth | 用户认证、JWT 管理 |
| projects.py | /api/projects | 项目 CRUD |
| documents.py | /api/documents | 文档上传和管理 |
| chat.py | /api/chat | RAG 问答 |
| analysis.py | /api/analysis | BA 分析流程 |

#### Services (`app/services/`)

| 服务 | 职责 |
|------|------|
| DatabaseService | SQLite 数据库操作 |
| VectorService | ChromaDB 向量存储和检索 |
| DocumentService | 文档解析和分块 |
| AnalysisService | 分析流程编排 |
| ExportService | DOCX 导出生成 |

#### Agents (`app/agents/`)

| Agent | 职责 | LLM 任务 |
|-------|------|----------|
| feature_extraction_agent | 特性提取 | 从文档分块提取功能特性 |
| interview_agent | 访谈生成 | 为每个特性生成 4 个澄清问题 |
| story_generation_agent | 故事生成 | 将特性转化为用户故事 |

---

## AI 分析流程

### 三步分析链

```
Step 1: Feature Extraction
┌─────────────────────────────────────────────────────┐
│  Input: Document Chunks (from ChromaDB)             │
│  Process: Map-Reduce extraction per chunk           │
│  Output: FeatureDraft[]                             │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
Step 2: Interview Generation
┌─────────────────────────────────────────────────────┐
│  Input: FeatureDraft[] + Truncated Document Context │
│  Process: Per-feature parallel question generation  │
│  Output: InterviewQuestion[] (4 per feature)        │
│                                                     │
│  Question Types:                                    │
│  • scope - 范围边界                                 │
│  • edge_case - 边缘情况                             │
│  • dependency - 依赖关系                             │
│  • business_value - 业务价值                        │
└─────────────────────────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
    Auto Mode                    Guided Mode
          │                           │
          ▼                           ▼
    Use suggested_answer       Wait for user answers
          │                           │
          └─────────────┬─────────────┘
                        │
                        ▼
Step 3: Story Generation
┌─────────────────────────────────────────────────────┐
│  Input: Features + Answers + Document Context       │
│  Process: Per-feature story generation              │
│  Output: Feature[] with UserStory[]                 │
│                                                     │
│  User Story Format:                                 │
│  • As a <role>                                      │
│  • I want <capability>                              │
│  • So that <benefit>                                │
│  • Acceptance Criteria (Given/When/Then)            │
└─────────────────────────────────────────────────────┘
```

### 分析模式对比

| 模式 | 流程 | 用户参与 |
|------|------|----------|
| Auto | Step 1 → Step 2 → Step 3 | 无需参与，自动完成 |
| Guided | Step 1 → Step 2 → 等待 → Step 3 | 编辑访谈答案后继续 |

---

## 数据流

### 文档上传流程

```
User Upload → FastAPI → Docling Serve
                           │
                           ▼
                     Parse to Markdown
                           │
                           ▼
                     Chunk Documents
                           │
                           ▼
                     OpenAI Embeddings
                           │
                           ▼
                     Store in ChromaDB
                           │
                           ▼
                     Save metadata to SQLite
```

### RAG 问答流程

```
User Question → OpenAI Embedding
                      │
                      ▼
               ChromaDB Query
                      │
                      ▼
               Top-K Relevant Chunks
                      │
                      ▼
               Azure OpenAI (GPT-4o)
                      │
                      ▼
               Generated Answer
                      │
                      ▼
               Response with Sources
```

---

## 安全架构

### 认证机制

```
┌─────────────────────────────────────────────────────────┐
│                     JWT Authentication                  │
│                                                         │
│  1. User Login → Verify Password (bcrypt)              │
│  2. Generate Tokens:                                    │
│     • access_token (expires in 60 min)                  │
│     • refresh_token (expires in 7 days)                 │
│  3. Client stores tokens in localStorage                │
│  4. Every request includes Authorization header         │
│  5. On 401: Auto-refresh using refresh_token            │
└─────────────────────────────────────────────────────────┘
```

### 授权检查

所有受保护端点使用 `Depends(get_current_user)` 进行认证：

```python
@router.get("/protected")
async def protected_route(
    current_user: CurrentUser = Depends(get_current_user)
):
    # Only authenticated users reach here
```

资源级别授权在路由中检查 `owner_id`：

```python
project = db.get_project(project_id)
if not project or project["owner_id"] != current_user.user_id:
    raise HTTPException(status_code=404, detail="Not found")
```

---

## 部署架构

### Azure Container Apps

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                     │
│                                                             │
│  ┌─────────────────┐        ┌─────────────────┐           │
│  │  Frontend       │        │   Backend       │           │
│  │  (Nginx + SPA)  │  ────► │   (FastAPI)     │           │
│  │  Port: 80       │        │   Port: 8000    │           │
│  └─────────────────┘        └─────────────────┘           │
│                                      │                      │
│                                      ▼                      │
│                             ┌─────────────────┐            │
│                             │  Azure OpenAI   │            │
│                             │  (GPT-4o)       │            │
│                             └─────────────────┘            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     External Services                        │
│                                                             │
│  ┌─────────────────┐        ┌─────────────────┐           │
│  │  Docling Serve  │        │   OpenAI API    │           │
│  │  (Document Parse)│       │   (Embeddings)  │           │
│  └─────────────────┘        └─────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### CI/CD 流水线

```yaml
# azure-pipelines.yml
Stages:
  1. Build:
     - Build backend Docker image
     - Build frontend Docker image
     - Push to Azure Container Registry

  2. Deploy:
     - Update backend container app
     - Update frontend container app
```

---

## 扩展性考虑

### 当前限制

| 限制 | 原因 | 解决方案 |
|------|------|----------|
| SQLite 单实例 | 嵌入式数据库 | 迁移到 PostgreSQL |
| ChromaDB 本地存储 | 无远程配置 | 使用 ChromaDB Cloud |
| 同步文档处理 | 单进程 | 使用任务队列 (Celery) |

### 推荐改进

1. **数据库升级** - SQLite → PostgreSQL + Supabase
2. **缓存层** - 添加 Redis 缓存频繁查询
3. **异步任务** - 使用 Celery/ARQ 处理长时间分析
4. **文件存储** - 使用 Azure Blob Storage 替代本地存储
