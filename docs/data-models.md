# 数据模型文档

**生成日期:** 2026-03-14

---

## 数据库 Schema

项目使用 SQLite 作为主数据库，ChromaDB 作为向量数据库。

### 表结构

#### users

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 主键 (UUID) |
| email | TEXT | 唯一邮箱 |
| display_name | TEXT | 显示名称 |
| password_hash | TEXT | bcrypt 密码哈希 |
| created_at | TEXT | 创建时间 (ISO 8601) |

#### projects

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 主键 (UUID) |
| name | TEXT | 项目名称 |
| description | TEXT | 项目描述 |
| owner_id | TEXT | 外键 → users.id |
| created_at | TEXT | 创建时间 |

#### documents

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 主键 (UUID) |
| project_id | TEXT | 外键 → projects.id |
| filename | TEXT | 原始文件名 |
| file_path | TEXT | 服务器存储路径 |
| file_type | TEXT | 文件类型 (pdf/docx) |
| total_pages | INTEGER | 总页数 |
| total_chunks | INTEGER | 分块数量 |
| cached_markdown | TEXT | 缓存的 Markdown 内容 |
| uploaded_at | TEXT | 上传时间 |

#### analysis_sessions

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 主键 (UUID) |
| project_id | TEXT | 外键 → projects.id |
| mode | TEXT | 分析模式 (auto/guided) |
| status | TEXT | 当前状态 |
| error_message | TEXT | 错误信息 |
| progress_message | TEXT | 进度信息 |
| feature_drafts_json | TEXT | 特性草案 (JSON) |
| questions_json | TEXT | 访谈问题 (JSON) |
| features_json | TEXT | 最终特性 (JSON) |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

---

## Pydantic 模型

### 认证模型

#### UserCreate
```python
class UserCreate(BaseModel):
    email: str
    password: str
    display_name: str
```

#### UserLogin
```python
class UserLogin(BaseModel):
    email: str
    password: str
```

#### UserResponse
```python
class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: str
```

#### TokenResponse
```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

#### CurrentUser
```python
class CurrentUser(BaseModel):
    user_id: str
    email: str
    display_name: str
```

---

### 文档模型

#### DocumentChunk
```python
class DocumentChunk(BaseModel):
    id: str           # 分块 ID
    doc_id: str       # 文档 ID
    doc_name: str     # 文档名称
    content: str      # 分块内容
    page: Optional[int] = None  # 页码
    position: Dict = {}         # 位置信息
```

#### Document
```python
class Document(BaseModel):
    id: str
    filename: str
    file_path: str
    file_type: str
    total_pages: int = 0
    total_chunks: int = 0
    uploaded_at: str
    project_id: Optional[str] = None
    cached_markdown: Optional[str] = None
```

---

### 分析模型

#### 枚举类型

```python
class QuestionType(str, Enum):
    scope = "scope"           # 范围问题
    edge_case = "edge_case"   # 边缘情况
    dependency = "dependency" # 依赖关系
    business_value = "business_value"  # 业务价值

class AnalysisMode(str, Enum):
    auto = "auto"       # 自动模式
    guided = "guided"   # 引导模式

class AnalysisStatus(str, Enum):
    extracting = "extracting"         # 提取中
    interviewing = "interviewing"     # 访谈生成中
    awaiting_answers = "awaiting_answers"  # 等待答案
    generating = "generating"         # 生成用户故事中
    done = "done"                     # 完成
    error = "error"                   # 错误
```

#### FeatureDraft (特性草案)

```python
class FeatureDraft(BaseModel):
    feature_id: str              # 特性 ID (如 F-001)
    title: str                   # 特性标题
    problem_statement: str       # 问题描述
    benefit: str                 # 业务收益
    business_process: str        # 关联业务流程
    scope: str                   # 范围边界
    sources: List[str] = []      # 来源引用
```

#### InterviewQuestion (访谈问题)

```python
class InterviewQuestion(BaseModel):
    question_id: str                    # 问题 ID (如 Q-001)
    feature_id: str                     # 关联特性 ID
    question: str                       # 问题内容
    question_type: QuestionType         # 问题类型
    suggested_answer: str               # AI 建议答案
    user_answer: Optional[str] = None   # 用户编辑答案
```

#### AcceptanceCriterion (验收标准)

```python
class AcceptanceCriterion(BaseModel):
    given: str   # 前置条件
    when: str    # 触发动作
    then: str    # 预期结果
```

#### UserStory (用户故事)

```python
class UserStory(BaseModel):
    story_id: str                        # 故事 ID (如 US-001)
    as_a: str                            # 角色
    i_want: str                          # 能力
    so_that: str                         # 目标
    acceptance_criteria: List[AcceptanceCriterion]  # 验收标准
    business_rules: List[str] = []       # 业务规则
    dependencies: List[str] = []         # 依赖项
```

#### Feature (完整特性)

```python
class Feature(BaseModel):
    feature_id: str
    title: str
    problem_statement: str
    benefit: str
    business_process: str
    scope: str
    sources: List[str] = []
    user_stories: List[UserStory]        # 生成的用户故事
```

---

### 请求/响应模型

#### StartAnalysisRequest
```python
class StartAnalysisRequest(BaseModel):
    mode: AnalysisMode = AnalysisMode.auto
```

#### SubmitAnswersRequest
```python
class SubmitAnswersRequest(BaseModel):
    answers: List[dict]  # [{question_id, user_answer}, ...]
```

#### AnalysisStatusResponse
```python
class AnalysisStatusResponse(BaseModel):
    session_id: str
    project_id: str
    mode: str
    status: str
    error_message: Optional[str] = None
    progress_message: Optional[str] = None
    feature_drafts: Optional[List[FeatureDraft]] = None
    questions: Optional[List[InterviewQuestion]] = None
    features: Optional[List[Feature]] = None
```

---

## 向量数据库 (ChromaDB)

### Collection 命名

每个项目创建一个独立的 Collection：
- 命名格式：`project_{project_id}`

### 文档结构

存储在 ChromaDB 中的向量文档：

```python
{
    "id": "chunk-uuid",
    "document": "分块文本内容",
    "embedding": [0.1, 0.2, ...],  # text-embedding-3-small
    "metadata": {
        "doc_id": "document-uuid",
        "doc_name": "document.pdf",
        "chunk_id": "chunk-uuid",
        "page": "5"  # 可选
    }
}
```

### 查询示例

```python
# 相似性搜索
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5
)

# 按文档 ID 过滤删除
collection.delete(where={"doc_id": "document-uuid"})
```

---

## 数据流图

```
用户上传文档
    ↓
Docling Serve 解析 → Markdown
    ↓
文档分块 → DocumentChunk[]
    ↓
OpenAI Embedding → 向量化
    ↓
存入 ChromaDB

---

用户提问
    ↓
问题向量化
    ↓
ChromaDB 相似性搜索
    ↓
返回相关分块
    ↓
LLM 生成答案
    ↓
返回给用户
```
