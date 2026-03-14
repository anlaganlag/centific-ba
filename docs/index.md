# BA Toolkit 项目文档

**生成日期:** 2026-03-14

---

## 项目概述

BA Toolkit 是一个 AI 驱动的业务分析工具包，帮助用户从文档中提取需求特性、生成访谈问题，并自动创建用户故事。

### 核心功能

- **文档管理** - 上传 PDF/DOCX 文档，自动解析和分块
- **智能问答** - 基于文档内容的 RAG 问答系统
- **需求提取** - AI 自动从文档中提取功能特性
- **访谈生成** - 生成澄清问题和建议答案
- **用户故事** - 自动生成带有验收标准的用户故事
- **导出功能** - 导出分析结果为 Word 文档

### 项目结构

```
ba-toolkit/
├── frontend/           # React + TypeScript + Vite
│   └── src/
│       ├── components/ # UI 组件
│       ├── pages/      # 路由页面
│       ├── stores/     # Zustand 状态管理
│       └── lib/        # API 客户端
├── backend/            # FastAPI + Python
│   └── app/
│       ├── api/routes/ # API 路由
│       ├── agents/     # AI 代理
│       ├── services/   # 业务逻辑
│       ├── models/     # Pydantic 模型
│       └── auth/       # 认证模块
└── docs/               # 项目文档
```

---

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **前端** | React | ^18.3.1 |
| | TypeScript | ^5.3.3 |
| | Vite | ^5.1.0 |
| | Zustand | ^4.5.0 |
| | TailwindCSS | ^3.4.1 |
| **后端** | FastAPI | >=0.109.0 |
| | Python | 3.11 |
| | Pydantic | >=2.10.0 |
| | Pydantic-AI | ==0.0.14 |
| | ChromaDB | >=0.4.22 |
| **AI 服务** | Azure OpenAI | gpt-4o |
| | Docling Serve | 文档解析 |
| **基础设施** | Docker | 容器化 |
| | Azure Container Apps | 部署平台 |

---

## 文档目录

### Part 1: API 合约

- [API 端点文档](./api-contracts.md) - 所有 REST API 端点的详细说明

### Part 2: 数据模型

- [数据模型文档](./data-models.md) - Pydantic 模型和数据库 Schema

### Part 3: 架构设计

- [系统架构](./architecture.md) - 系统架构和设计决策

---

## 快速开始

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API 密钥
uvicorn app.main:app --port 8001

# 前端
cd frontend
npm install
npm run dev
```

### Docker 部署

```bash
docker-compose up -d
```

---

## 环境变量

### 后端必需变量

| 变量 | 说明 |
|------|------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API 密钥 |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI 端点 URL |
| `AZURE_OPENAI_DEPLOYMENT` | 模型部署名称 (默认: gpt-4o) |
| `OPENAI_API_KEY` | OpenAI API 密钥 (用于 Embeddings) |
| `JWT_SECRET_KEY` | JWT 签名密钥 (至少 32 字符) |
| `DOCLING_SERVE_URL` | Docling 服务 URL |

### 前端可选变量

| 变量 | 说明 |
|------|------|
| `VITE_API_URL` | API 基础 URL (默认: /api) |

---

## 相关文档

- [项目上下文](../_bmad-output/project-context.md) - AI 代理实现规则
