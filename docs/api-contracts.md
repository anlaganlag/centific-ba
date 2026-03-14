# API 合约文档

**生成日期:** 2026-03-14

---

## 认证

所有受保护的端点需要在请求头中携带 JWT Token：

```
Authorization: Bearer <access_token>
```

Token 过期时可通过 refresh_token 自动刷新。

---

## 认证端点 (`/api/auth`)

### POST /api/auth/register

注册新用户。

**请求体：**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "display_name": "User Name"
}
```

**响应：**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**错误：**
- `400` - 邮箱已被注册

---

### POST /api/auth/login

用户登录。

**请求体：**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应：**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**错误：**
- `401` - 邮箱或密码错误

---

### POST /api/auth/refresh

刷新访问令牌。

**查询参数：**
- `refresh_token` (string) - 刷新令牌

**响应：**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### GET /api/auth/me

获取当前用户信息。

**认证：** 需要

**响应：**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "User Name",
  "created_at": "2026-03-14T10:00:00"
}
```

---

## 项目端点 (`/api/projects`)

### POST /api/projects

创建新项目。

**认证：** 需要

**请求体：**
```json
{
  "name": "My Project",
  "description": "Project description"
}
```

**响应：**
```json
{
  "id": "uuid",
  "name": "My Project",
  "description": "Project description",
  "owner_id": "user-uuid",
  "created_at": "2026-03-14T10:00:00",
  "document_count": 0
}
```

---

### GET /api/projects

列出当前用户的所有项目。

**认证：** 需要

**响应：**
```json
[
  {
    "id": "uuid",
    "name": "Project 1",
    "description": "",
    "owner_id": "user-uuid",
    "created_at": "2026-03-14T10:00:00",
    "document_count": 3
  }
]
```

---

### GET /api/projects/{project_id}

获取单个项目详情。

**认证：** 需要

**响应：**
```json
{
  "id": "uuid",
  "name": "Project Name",
  "description": "",
  "owner_id": "user-uuid",
  "created_at": "2026-03-14T10:00:00",
  "document_count": 3
}
```

**错误：**
- `404` - 项目不存在或无权限

---

### DELETE /api/projects/{project_id}

删除项目及其所有文档。

**认证：** 需要

**响应：**
```json
{
  "detail": "Project deleted"
}
```

---

## 文档端点 (`/api/documents`)

### POST /api/documents/upload/{project_id}

上传文档到项目。

**认证：** 需要

**请求类型：** `multipart/form-data`

**参数：**
- `files` (file[]) - 一个或多个文档文件

**响应：**
```json
{
  "documents": [
    {
      "doc_id": "uuid",
      "filename": "document.pdf",
      "total_pages": 10,
      "total_chunks": 45,
      "status": "success"
    }
  ]
}
```

**错误：**
- `404` - 项目不存在
- `status: error` - 单个文件处理失败

---

### GET /api/documents/{project_id}

列出项目的所有文档。

**认证：** 需要

**响应：**
```json
{
  "documents": [
    {
      "id": "uuid",
      "filename": "document.pdf",
      "file_type": "pdf",
      "total_pages": 10,
      "total_chunks": 45,
      "uploaded_at": "2026-03-14T10:00:00"
    }
  ]
}
```

---

### DELETE /api/documents/{doc_id}

删除文档及其向量数据。

**认证：** 需要

**响应：**
```json
{
  "detail": "Document deleted"
}
```

---

## 聊天端点 (`/api/chat`)

### POST /api/chat/{project_id}

与文档进行问答对话。

**认证：** 需要

**请求体：**
```json
{
  "question": "What are the main features?",
  "history": [
    {"role": "user", "content": "Previous question"},
    {"role": "assistant", "content": "Previous answer"}
  ]
}
```

**响应：**
```json
{
  "answer": "Based on the documents...",
  "sources": [
    {
      "doc_name": "document.pdf",
      "page": 5,
      "excerpt": "Relevant text..."
    }
  ],
  "confidence": 0.85,
  "requires_clarification": false,
  "clarification_question": null
}
```

---

## 分析端点 (`/api/analysis`)

### POST /api/analysis/{project_id}/start

启动 BA 分析流程。

**认证：** 需要

**请求体：**
```json
{
  "mode": "auto" | "guided"
}
```

**响应：**
```json
{
  "session_id": "uuid",
  "project_id": "uuid",
  "mode": "auto",
  "status": "extracting",
  "progress_message": "Extracting features from 10 chunks..."
}
```

**错误：**
- `400` - 项目没有上传文档
- `404` - 项目不存在

---

### GET /api/analysis/{project_id}/status

获取分析状态和结果。

**认证：** 需要

**响应：**
```json
{
  "session_id": "uuid",
  "project_id": "uuid",
  "mode": "auto",
  "status": "done",
  "progress_message": "Done — 5 features, 15 user stories",
  "feature_drafts": [...],
  "questions": [...],
  "features": [...]
}
```

**状态值：**
- `extracting` - 特性提取中
- `interviewing` - 生成访谈问题中
- `awaiting_answers` - 等待用户确认 (guided 模式)
- `generating` - 生成用户故事中
- `done` - 完成
- `error` - 错误

---

### POST /api/analysis/{project_id}/answers

提交用户编辑的答案 (仅 guided 模式)。

**认证：** 需要

**请求体：**
```json
{
  "answers": [
    {
      "question_id": "Q-001",
      "user_answer": "User's edited answer"
    }
  ]
}
```

**响应：**
```json
{
  "session_id": "uuid",
  "project_id": "uuid",
  "mode": "guided",
  "status": "generating",
  "progress_message": "Generating user stories..."
}
```

---

### GET /api/analysis/{project_id}/export

导出分析结果为 DOCX 文件。

**认证：** 需要

**响应：** Word 文件下载

**错误：**
- `400` - 分析未完成或无特性数据

---

## 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "detail": "Error message description"
}
```

**常见 HTTP 状态码：**
- `400` - 请求参数错误
- `401` - 未认证或 Token 过期
- `404` - 资源不存在
- `500` - 服务器内部错误
