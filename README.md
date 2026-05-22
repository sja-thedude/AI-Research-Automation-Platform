# 🧠 NeuraForge AI — AI Research & Automation Platform

> A production-grade, AI-first platform where teams **upload documents, research
> topics, summarize content, automate workflows, train AI assistants, and build
> knowledge bases** — think *Notion AI × ChatGPT × Perplexity × Zapier*, built
> on Django.

Built with **Django 5 · DRF · PostgreSQL + pgvector · Redis · Celery · Django
Channels (WebSockets) · LangChain · OpenAI**.

---

## ✨ Features

| Area | What's included |
|------|-----------------|
| 🔐 **Auth & Teams** | Email-based JWT auth (access/refresh + rotation + blacklist), profiles, role-based team collaboration, object-level permissions |
| 📄 **Documents** | Upload PDF / DOCX / TXT / CSV / XLSX / images, async text extraction, **OCR**, dedup by content hash, folders/file-explorer |
| 🤖 **AI Engine (RAG)** | LangChain RAG pipeline with **inline citations**, embeddings, summarization (short/long/research/insights), trainable **AI assistants**, **multi-agent** orchestration |
| 🔎 **Search** | **Hybrid** semantic (vector) + Postgres full-text search with Reciprocal Rank Fusion |
| 🗒️ **Notes** | AI-enhanced notes, auto-summaries/tags, **bidirectional knowledge linking** (wikilinks) |
| ⚙️ **Automation** | Zapier-style **workflow builder**: manual / scheduled / event / webhook triggers, pluggable action registry, run history |
| 🕸️ **Knowledge Graph** | Entities + typed relationships, graph API for visualization |
| ⚡ **Realtime** | WebSocket **token-streaming chat** (ChatGPT-style) + per-user notification channel |
| 🏗️ **Platform** | Modular apps, versioned API, OpenAPI/Swagger docs, structured logging, health probes, Dockerized, Celery queues, Sentry-ready |

---

## 🏛️ Architecture

```
                         ┌──────────────────────────────┐
   Web / Mobile ────────▶│  Nginx / Load Balancer (TLS) │
   (REST + WebSocket)    └───────────────┬──────────────┘
                                         │ HTTP + ws://
                          ┌──────────────▼───────────────┐
                          │   ASGI app (uvicorn/daphne)   │
                          │   Django 5 · DRF · Channels   │
                          └───┬───────────────────────┬───┘
            REST API (/api/v1)│                       │ WebSocket (/ws)
       ┌──────────────────────▼───┐         ┌─────────▼─────────────┐
       │ accounts documents notes │         │ chat consumers        │
       │ ai_engine search         │         │ (streaming RAG +       │
       │ automation knowledge     │         │  notifications)        │
       └───────┬──────────────┬───┘         └───────────┬───────────┘
               │              │                         │
        ┌──────▼──────┐  ┌────▼─────┐          ┌────────▼────────┐
        │ PostgreSQL  │  │  Redis   │◀────────▶│ Celery workers  │
        │ + pgvector  │  │ cache /  │  broker  │ documents · ai  │
        │ (vectors +  │  │ channels │  results │ automation      │
        │  relational)│  │ / broker │          │ + Celery beat   │
        └─────────────┘  └──────────┘          └────────┬────────┘
                                                        │
                                          ┌─────────────▼──────────────┐
                                          │ LangChain → OpenAI (LLM +   │
                                          │ embeddings) · OCR · parsers │
                                          └─────────────────────────────┘
```

**Modular apps** (`apps/`):

```
core/        Base models (UUID, timestamps, soft-delete), permissions, pagination, health
accounts/    Custom User, JWT auth, profiles, Teams + role-based membership
documents/   Upload, multi-format extraction (+OCR), ingestion pipeline
ai_engine/   Vector store abstraction, embeddings, RAG, summarization, agents,
             AIAssistant + Conversation/Message (chat history & citations)
search/      Semantic / full-text / hybrid (RRF) search + analytics
notes/       AI notes, tags, NoteLink knowledge graph
automation/  Workflow + Step + Run, action registry, execution engine
knowledge/   Entities + Relationships (knowledge graph) + graph API
chat/        Channels JWT middleware, streaming chat & notification consumers
```

### Data model highlights (vector-ready)

- **`ai_engine.KnowledgeChunk`** — the unified vector store. Any source
  (Document, Note, …) is chunked + embedded into this table via a **generic
  relation**, indexed with **pgvector HNSW** (`vector_cosine_ops`). Retrieval is
  source-agnostic and tenant-scoped (owner/team).
- **`ai_engine.AIAssistant`** — configurable/"trainable" agents (persona, model,
  tools, knowledge scope).
- **`ai_engine.Conversation` / `Message`** — chat history with **citation
  tracking** and token usage.
- **`automation.Workflow` / `WorkflowStep` / `WorkflowRun`** — workflow tables.
- **`knowledge.Entity` / `Relationship`** — property-graph knowledge models.

---

## 🚀 Quickstart

```bash
git clone <this-repo> && cd AI-Research-Automation-Platform
cp .env.example .env            # set OPENAI_API_KEY (+ secret key) at minimum

make build && make up           # Postgres+pgvector, Redis, web, worker, beat, flower
make makemigrations && make migrate
make superuser
make seed                       # optional: demo@neuraforge.ai / demo12345
```

Open:
- **Swagger UI** → http://localhost:8000/api/docs/
- **ReDoc** → http://localhost:8000/api/redoc/
- **Admin** → http://localhost:8000/admin/
- **Flower** → http://localhost:5555

Full instructions (bare-metal, production, k8s, managed Postgres) →
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## 🔌 API overview

All endpoints are versioned under `/api/v1/` and (except auth/health) require a
`Authorization: Bearer <access_jwt>` header.

### Auth
```
POST /api/v1/auth/register/           Self-service signup
POST /api/v1/auth/login/              → { access, refresh, user }
POST /api/v1/auth/refresh/            Rotate access token
POST /api/v1/auth/logout/             Blacklist refresh token
GET  /api/v1/auth/me/                 Current user + profile
GET  /api/v1/auth/teams/              Teams; /teams/{id}/members/ to invite
```

### Documents
```
POST /api/v1/documents/               multipart upload → async extract+index
GET  /api/v1/documents/               list (filter by file_type/status/folder)
POST /api/v1/documents/{id}/summarize/  queue AI summary
POST /api/v1/documents/{id}/reprocess/  re-run ingestion
```

### AI Engine
```
POST /api/v1/ai/chat/                 RAG answer with citations (persisted)
POST /api/v1/ai/summarize/            { text, mode: short|long|research|insights }
POST /api/v1/ai/agents/run/           multi-agent research pipeline (async)
CRUD /api/v1/ai/assistants/           build trainable AI assistants
CRUD /api/v1/ai/conversations/        chat history
```

### Search / Notes / Automation / Knowledge
```
GET  /api/v1/search/?q=...&mode=hybrid|semantic|fulltext
CRUD /api/v1/notes/                   + /{id}/link/  /{id}/backlinks/
CRUD /api/v1/automation/workflows/    + /{id}/run/  /{id}/runs/  /actions/
GET  /api/v1/knowledge/graph/         nodes + edges for visualization
```

### WebSocket (realtime)
```
ws://localhost:8000/ws/chat/<conversation_id>/?token=<access_jwt>
   → send {"question": "...", "source_ids": [...], "top_k": 6}
   ← stream {type: "citations"} {type: "token"} ... {type: "done"}

ws://localhost:8000/ws/notifications/?token=<access_jwt>
   ← {event: "document.status", data: {...}}   # e.g. indexing finished
```

### Example: ask a question over your documents

```bash
curl -X POST http://localhost:8000/api/v1/ai/chat/ \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"question": "What were the key findings?", "top_k": 6}'
# → { "answer": "... [1][2]", "citations": [{ref, source_id, snippet, score}], ... }
```

---

## 🧩 Extending the platform (built-in extension points)

The architecture is prepared for future AI expansion — each advanced capability
has a clean seam:

| Capability | Where to plug in |
|------------|------------------|
| **Multi-agent systems** | `ai_engine/services/agents.py` (`Agent`, `Orchestrator`) |
| **RAG tuning** | `ai_engine/services/rag.py`, `retrieval.py`, `ingestion.py` |
| **Alt vector DBs** (Chroma/Pinecone/Weaviate) | implement the `VectorStore` protocol in `ai_engine/services/vector_store.py` |
| **OCR / new file types** | register an extractor in `documents/extractors.py` |
| **Workflow actions** (browser automation, email, Slack, report/slide gen) | `@action(...)` in `automation/actions.py` |
| **Knowledge-graph extraction** | populate `knowledge.Entity/Relationship` from a Celery task over `KnowledgeChunk` |
| **Voice / vision / video summarization** | add extractors + Celery tasks; reuse the same ingestion → vector → RAG path |
| **New LLM provider** | swap clients in `ai_engine/services/llm.py` |

---

## 🛠️ Tech stack

**Backend:** Django 5, Django REST Framework, drf-spectacular (OpenAPI)
**Async:** Celery + Redis (3 queues), django-celery-beat, Channels + channels-redis
**AI:** LangChain, langchain-openai, OpenAI, tiktoken
**Data:** PostgreSQL 16, pgvector (HNSW), Postgres full-text search
**Docs/Parsing:** pypdf, python-docx, openpyxl, Pillow, pytesseract (OCR)
**Infra:** Docker, gunicorn + uvicorn workers, WhiteNoise, django-storages (S3/R2)
**Quality:** pytest, ruff, black, mypy + django-stubs, Sentry

---

## 🧪 Tests & quality

```bash
make test          # pytest (smoke tests for auth, teams, health)
make lint          # ruff
make fmt           # black + ruff --fix
python manage.py check --deploy   # production readiness checks
```

---

## 📁 Project layout

```
config/            settings (base/dev/prod), urls, asgi, wsgi, celery
apps/              modular Django apps (see Architecture)
requirements/      base.txt · dev.txt · prod.txt
docker/            Dockerfile · entrypoint.sh
docs/              DEPLOYMENT.md
docker-compose.yml Makefile  pyproject.toml  conftest.py  .env.example
```

---

## 📝 License

Released for development use. Add your preferred license before distribution.
