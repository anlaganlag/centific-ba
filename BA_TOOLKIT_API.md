# BA Toolkit API Documentation

**Base URL:** `https://ba-toolkit-backend.nicemoss-edd0d815.eastus.azurecontainerapps.io`

**Swagger UI:** `https://ba-toolkit-backend.nicemoss-edd0d815.eastus.azurecontainerapps.io/docs`

**Authentication:** JWT Bearer token. All endpoints except register, login, refresh and health require `Authorization: Bearer <token>` header.

---

## How to Get a Token

### 1. Register a new user

```bash
curl -X POST .../api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "mypassword",
    "display_name": "John Doe"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

### 2. Login with existing user

```bash
curl -X POST .../api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "mypassword"
  }'
```

Returns the same `access_token` + `refresh_token`.

### 3. Use the token

Add this header to all subsequent requests:

```
Authorization: Bearer eyJhbG...
```

### 4. Refresh an expired token

Access tokens expire after 60 minutes. Use the refresh token to get a new one:

```bash
curl -X POST ".../api/auth/refresh?refresh_token=eyJhbG..."
```

Returns new `access_token` + `refresh_token`. Refresh tokens expire after 7 days.

### 5. Get current user info

```bash
curl .../api/auth/me \
  -H "Authorization: Bearer eyJhbG..."
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "John Doe",
  "created_at": "2026-02-25T..."
}
```

---

## Projects

Projects are containers for documents and analysis sessions. Each user has their own projects.

### POST `/api/projects` — Create project

```bash
curl -X POST .../api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-Commerce Replatform",
    "description": "Discovery analysis for e-commerce project"
  }'
```

**Response:**
```json
{
  "id": "b6c709b7-...",
  "name": "E-Commerce Replatform",
  "description": "Discovery analysis for e-commerce project",
  "owner_id": "c4d8bae9-...",
  "created_at": "2026-02-25T...",
  "document_count": 0
}
```

### GET `/api/projects` — List all projects

Returns array of all projects owned by the authenticated user, sorted by creation date (newest first). Each project includes `document_count`.

### GET `/api/projects/{project_id}` — Get single project

Returns one project by ID. Returns 404 if not found or not owned by current user.

### DELETE `/api/projects/{project_id}` — Delete project

Deletes project and **cascades**: removes all documents, vector embeddings, and analysis sessions linked to it.

---

## Documents

Documents are uploaded files (PDF, DOCX, PPTX, TXT, images) that get parsed through Docling Serve into markdown, then chunked and embedded into ChromaDB for RAG.

### POST `/api/documents/upload/{project_id}` — Upload documents

Upload one or more files. Each file goes through this pipeline:
1. File saved to disk
2. Sent to Docling Serve for parsing → returns markdown + page count
3. Markdown chunked (3000 chars, 300 char overlap)
4. Chunks embedded via OpenAI `text-embedding-3-small`
5. Embeddings stored in ChromaDB
6. Metadata saved to SQLite

```bash
curl -X POST .../api/documents/upload/b6c709b7-... \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@requirements.pdf" \
  -F "files=@discovery_notes.docx"
```

**Response:**
```json
{
  "documents": [
    {
      "doc_id": "28893520-...",
      "filename": "requirements.pdf",
      "total_pages": 12,
      "total_chunks": 8,
      "status": "success"
    },
    {
      "doc_id": "a1b2c3d4-...",
      "filename": "discovery_notes.docx",
      "total_pages": 5,
      "total_chunks": 3,
      "status": "success"
    }
  ]
}
```

**Supported formats:** PDF, DOCX, PPTX, TXT, PNG, JPG, TIFF, HTML

### GET `/api/documents/{project_id}` — List documents

Returns all documents in a project with metadata (filename, file_type, total_pages, total_chunks, uploaded_at).

### DELETE `/api/documents/{doc_id}` — Delete document

Deletes document file from disk, removes chunks from ChromaDB, and deletes metadata from SQLite.

---

## Chat (RAG Q&A)

Ask questions about uploaded documents. Uses Retrieval Augmented Generation — finds the 5 most relevant document chunks via ChromaDB vector search, then sends them to Azure OpenAI GPT-4o to generate an answer.

### POST `/api/chat/{project_id}` — Ask a question

```bash
curl -X POST .../api/chat/b6c709b7-... \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main business goals?",
    "history": []
  }'
```

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | The question to ask |
| `history` | array | No | Previous messages for context: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]` |

**Response:**
```json
{
  "answer": "The main business goals are: 1) Increase online sales by 30%...",
  "sources": [
    {
      "doc_name": "requirements.pdf",
      "page": 3,
      "excerpt": "Increase online sales by 30% within 12 months"
    }
  ],
  "confidence": 0.92,
  "requires_clarification": false,
  "clarification_question": null
}
```

**Confidence levels:**
- **0.9–1.0:** Direct, explicit information found in documents
- **0.7–0.89:** Implied or inferred from context
- **0.5–0.69:** Vague or uncertain

If the answer is not in the documents, the AI explicitly says so and returns low confidence.

---

## Analysis (BA Chain)

The core feature. A 3-step AI pipeline that analyzes all uploaded documents and generates structured BA output.

### How the chain works

```
Step 1: Feature Extraction
  → AI reads all documents, extracts 3-15 distinct features
  → Each feature has: title, problem statement, benefit, business process, scope, sources

Step 2: Interview Q&A
  → For each feature, AI generates 4 questions (scope, edge case, dependency, business value)
  → Each question has an AI-suggested answer based on documents

Step 3: Story Generation
  → Using features + answered questions, AI generates 2-4 user stories per feature
  → Each story has: As a/I want/So that + Given/When/Then acceptance criteria
```

**Two modes:**
- **Auto:** All 3 steps run automatically. AI uses its own suggested answers for step 3.
- **Guided:** Steps 1-2 run, then pauses. User reviews/edits interview answers. After submitting, step 3 runs with user's answers.

---

### POST `/api/analysis/{project_id}/start` — Start analysis

```bash
curl -X POST .../api/analysis/b6c709b7-.../start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "auto"}'
```

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `"auto"` | `"auto"` — AI handles everything. `"guided"` — pauses for user input after step 2. |

**Response:** `AnalysisStatusResponse` (see below)

**Important:** This endpoint returns **immediately** with status `extracting`. The analysis runs as a background task. Poll `GET /status` every 2-3 seconds to track progress.

**Auto mode:** All 3 steps run in background. Poll until status is `done`.

**Guided mode:** Steps 1-2 run in background. Poll until status is `awaiting_answers`. Submit answers with the `/answers` endpoint to trigger step 3 (also runs in background).

**How it works internally (map-reduce):**
1. Step 1 uses map-reduce to handle large documents without hitting token limits:
   - **Map:** Each document chunk is processed individually in parallel (extracts partial features)
   - **Reduce:** All partial features are merged and deduplicated into 3-15 final features
2. Step 2 generates 4 interview questions per feature (one per type: scope, edge_case, dependency, business_value)
3. Step 3 generates 2-5 user stories per feature with Given/When/Then acceptance criteria

---

### GET `/api/analysis/{project_id}/status` — Get analysis status

```bash
curl .../api/analysis/b6c709b7-.../status \
  -H "Authorization: Bearer $TOKEN"
```

Returns the latest analysis session for this project. **Poll this every 2-3 seconds** while analysis is running to get real-time progress updates.

**Status values:**

| Status | Description |
|--------|-------------|
| `extracting` | Step 1 running — extracting features from documents (map-reduce) |
| `interviewing` | Step 2 running — generating interview questions |
| `awaiting_answers` | Guided mode only — waiting for user to submit answers |
| `generating` | Step 3 running — generating user stories |
| `done` | Complete — all results available |
| `error` | Failed — check `error_message` field |

**Response:** `AnalysisStatusResponse`
```json
{
  "session_id": "766588de-...",
  "project_id": "b6c709b7-...",
  "mode": "auto",
  "status": "done",
  "error_message": null,
  "progress_message": "Done — 15 features, 61 user stories",
  "feature_drafts": [
    {
      "feature_id": "F-001",
      "title": "Advanced Search with Filters",
      "problem_statement": "Basic search has no filters...",
      "benefit": "Improves product discovery...",
      "business_process": "Product Discovery",
      "scope": "Filters for price, category, brand, ratings",
      "sources": ["Key Features > Product Catalog > Advanced search"]
    }
  ],
  "questions": [
    {
      "question_id": "Q-001",
      "feature_id": "F-001",
      "question": "What product categories need filters?",
      "question_type": "scope",
      "suggested_answer": "All categories including electronics, apparel...",
      "user_answer": "All categories including electronics, apparel..."
    }
  ],
  "features": [
    {
      "feature_id": "F-001",
      "title": "Advanced Search with Filters",
      "problem_statement": "...",
      "benefit": "...",
      "business_process": "Product Discovery",
      "scope": "...",
      "sources": ["..."],
      "user_stories": [
        {
          "story_id": "US-001",
          "as_a": "customer",
          "i_want": "to filter search results by price, category, brand, and ratings",
          "so_that": "I can find products matching my requirements easily",
          "acceptance_criteria": [
            {
              "given": "I am on the search page",
              "when": "I select filters for price range and category",
              "then": "I see only products matching the selected criteria"
            }
          ],
          "business_rules": ["Filters update dynamically based on available products"],
          "dependencies": ["Requires structured product data in backend"]
        }
      ]
    }
  ]
}
```

---

### POST `/api/analysis/{project_id}/answers` — Submit interview answers (guided mode)

Only works when status is `awaiting_answers`. Submit edited answers and trigger step 3.

```bash
curl -X POST .../api/analysis/b6c709b7-.../answers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {"question_id": "Q-001", "user_answer": "Only electronics and apparel need filters initially"},
      {"question_id": "Q-002", "user_answer": "Show warning message if no results match"},
      {"question_id": "Q-003", "user_answer": "Depends on product database restructuring"},
      {"question_id": "Q-004", "user_answer": "High priority - directly impacts conversion rate"}
    ]
  }'
```

Any questions not included in the `answers` array will fall back to the AI's `suggested_answer`.

**Response:** `AnalysisStatusResponse` with status `done` and all results.

---

### GET `/api/analysis/{project_id}/export` — Download DOCX report

Returns a Word document with the full analysis: features overview table, detailed feature sections, and user stories with acceptance criteria.

```bash
curl -o report.docx .../api/analysis/b6c709b7-.../export \
  -H "Authorization: Bearer $TOKEN"
```

**Response:** Binary DOCX file with `Content-Disposition: attachment` header.

Only works when analysis status is `done`. Returns 400 if analysis is not complete.

**DOCX structure:**
- Title page: "{Project Name} — BA Analysis Report"
- Features overview table (ID, Feature, Problem, Business Process)
- For each feature:
  - Problem Statement
  - Benefit
  - Business Process
  - Scope
  - Sources
  - User Stories with Given/When/Then acceptance criteria

---

## Complete Workflow Example

```bash
BASE="https://ba-toolkit-backend.nicemoss-edd0d815.eastus.azurecontainerapps.io"

# 1. Register
TOKEN=$(curl -s -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"analyst@company.com","password":"secure123","display_name":"BA User"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Create project
PROJECT_ID=$(curl -s -X POST $BASE/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Client Discovery","description":"Q1 2026 project analysis"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Upload documents
curl -X POST $BASE/api/documents/upload/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@discovery_call.pdf" \
  -F "files=@requirements.docx" \
  -F "files=@stakeholder_notes.pptx"

# 4. Ask questions about documents (optional)
curl -X POST $BASE/api/chat/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Who are the key stakeholders?"}'

# 5. Run analysis (auto mode) — returns immediately
curl -X POST $BASE/api/analysis/$PROJECT_ID/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"auto"}'

# 6. Poll status until done (check progress_message for real-time updates)
# Example progress_message values:
#   "Extracting features from chunk 45/120"
#   "Merging and deduplicating features..."
#   "Generating interview questions..."
#   "Generating user stories..."
#   "Done — 15 features, 61 user stories"
while true; do
  STATUS=$(curl -s $BASE/api/analysis/$PROJECT_ID/status \
    -H "Authorization: Bearer $TOKEN")
  echo $STATUS | python -c "import sys,json;d=json.load(sys.stdin);print(d['status'], '|', d.get('progress_message',''))"
  S=$(echo $STATUS | python -c "import sys,json;print(json.load(sys.stdin)['status'])")
  [ "$S" = "done" ] || [ "$S" = "error" ] && break
  sleep 3
done

# 7. Download DOCX report (only works when status is "done")
curl -o BA_Report.docx $BASE/api/analysis/$PROJECT_ID/export \
  -H "Authorization: Bearer $TOKEN"
```

---

## Error Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad request — missing documents, analysis not complete, etc. |
| 401 | Unauthorized — missing or expired token |
| 404 | Not found — project doesn't exist or not owned by user |
| 422 | Validation error — check request body format |
| 500 | Internal server error |
