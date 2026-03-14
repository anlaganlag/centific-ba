# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

BA Toolkit — a Business Analyst assistant that ingests project documents, extracts features, generates interview questions, and produces user stories with acceptance criteria. It uses a 3-step AI pipeline powered by Azure OpenAI (via pydantic-ai agents) and stores documents in ChromaDB for vector search.

## Development Commands

### Backend (Python/FastAPI)
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # then fill in API keys
uvicorn app.main:app --reload --port 8001
```

### Frontend (React/Vite)
```bash
cd frontend
npm install
npm run dev          # starts on port 5173, proxies /api to localhost:8001
npm run build        # tsc -b && vite build
```

### Docker (full stack)
```bash
docker-compose up    # backend on :8000, frontend on :3000
```

### Deploy to Azure Container Apps
```bash
chmod +x infra/deploy.sh && ./infra/deploy.sh
```
CI/CD is configured via `azure-pipelines.yml` — triggers on push to `main`, builds images to ACR `crswatteam01`, deploys to Azure Container Apps in resource group `rg-ba-toolkit`.

## Architecture

### Analysis Pipeline (the core logic)
The analysis runs as a 3-step async pipeline in `backend/app/services/analysis_service.py`:

1. **Feature Extraction** (`agents/feature_extraction_agent.py`) — Map-Reduce pattern: maps each document chunk through a pydantic-ai agent to extract partial features, then reduces/deduplicates into 3-15 final features (F-001, F-002, ...).
2. **Interview Generation** (`agents/interview_agent.py`) — Generates 4 clarifying questions per feature (scope, edge_case, dependency, business_value). In **auto** mode, uses AI-suggested answers. In **guided** mode, pauses at `awaiting_answers` status for user input.
3. **Story Generation** (`agents/story_generation_agent.py`) — Produces 2-4 user stories per feature with Given/When/Then acceptance criteria.

All three agents use Azure OpenAI via `pydantic-ai` with `AzureProvider`. Concurrency is limited to 3-5 parallel tasks via `asyncio.Semaphore` to avoid rate limits.

Analysis sessions are persisted in SQLite with status polling — the frontend polls `GET /api/analysis/{project_id}/status` to track progress through states: `extracting → interviewing → awaiting_answers (guided only) → generating → done`.

### Document Processing
`backend/app/services/document_service.py` sends uploaded files to an external **Docling Serve** instance (configured via `DOCLING_SERVE_URL`) for PDF/DOCX/PPTX→markdown conversion. TXT files are processed directly. Documents are chunked (3000 chars, 300 overlap) and stored in ChromaDB with OpenAI `text-embedding-3-small` embeddings.

### Data Storage
- **SQLite** (`data/app.db`) — users, projects, documents, analysis_sessions. Schema is auto-created in `db_service.py:init_database()`.
- **ChromaDB** (`data/vectors/`) — document chunks with embeddings, one collection per project (`project_{id}`). Supports local persistent mode or remote HTTP mode via `CHROMADB_HOST`.
- **File uploads** — saved to `data/uploads/`.

### Auth
JWT-based (access + refresh tokens). Auth middleware in `backend/app/auth/`. Frontend stores tokens in localStorage and auto-refreshes on 401 via axios interceptor (`frontend/src/lib/api.ts`).

### Frontend
React 18 + TypeScript + Vite + Tailwind CSS + Zustand for auth state. Routes: `/login`, `/register`, `/` (dashboard), `/projects/:projectId`. API base URL configurable via `VITE_API_URL` env var (defaults to `/api` which Vite proxies to backend).

### API Routes
All backend routes are under `/api/` prefix:
- `auth` — register, login, refresh
- `projects` — CRUD for projects
- `documents` — upload, list, delete (per project)
- `chat` — RAG-based Q&A against project documents
- `analysis` — start analysis, poll status, submit answers (guided mode)

## Key Environment Variables
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` — for pydantic-ai agents
- `OPENAI_API_KEY` — for ChromaDB embeddings (uses standard OpenAI, not Azure)
- `DOCLING_SERVE_URL` — external document conversion service
- `JWT_SECRET_KEY` — must be changed from default in production
