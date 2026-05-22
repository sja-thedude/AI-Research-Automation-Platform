# NeuraForge AI — Deployment Guide

This guide covers local development, staging, and production deployment.

---

## 1. Prerequisites

| Dependency | Version | Notes |
|------------|---------|-------|
| Docker + Compose | 24+ | Easiest path; bundles Postgres+pgvector & Redis |
| Python | 3.12 | For bare-metal/local dev without Docker |
| PostgreSQL | 16 + `pgvector` | Use the `pgvector/pgvector:pg16` image |
| Redis | 7 | Cache, Channels layer, Celery broker/result |
| OpenAI API key | — | Or any LangChain-compatible provider |

---

## 2. Local development (Docker — recommended)

```bash
cp .env.example .env          # fill in OPENAI_API_KEY at minimum
make build                    # build images
make up                       # start db, redis, web, worker, beat, flower
make makemigrations           # first run only
make migrate
make superuser                # create admin login
make seed                     # optional demo data (demo@neuraforge.ai / demo12345)
```

Services:
- API + WebSocket → http://localhost:8000
- Swagger UI → http://localhost:8000/api/docs/
- Django admin → http://localhost:8000/admin/
- Flower (Celery) → http://localhost:5555
- Health probe → http://localhost:8000/health/

Tail logs with `make logs`. Run tests with `make test`.

---

## 3. Local development (bare metal)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt

# Start Postgres (with pgvector) and Redis yourself, then:
export DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py makemigrations
python manage.py migrate
python manage.py runserver            # HTTP + WS via daphne/ASGI

# In separate terminals:
celery -A config worker -l info -Q documents,ai,automation,celery
celery -A config beat   -l info
```

> The `pgvector` extension is enabled automatically by migration
> `apps/ai_engine/migrations/0001_enable_pgvector.py`. The DB role must be
> allowed to `CREATE EXTENSION` (superuser locally, or pre-create the extension
> on managed Postgres — see §5).

---

## 4. Configuration reference

All config is environment-driven (`config/settings/*`, read via `.env`).
Key variables (full list in `.env.example`):

- `DJANGO_SETTINGS_MODULE` — `config.settings.dev` | `config.settings.prod`
- `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CHANNELS_REDIS_URL`
- `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, `OPENAI_EMBEDDING_MODEL`, `OPENAI_EMBEDDING_DIM`
- `VECTOR_BACKEND` — `pgvector` (default) | `chroma` | `pinecone` | `weaviate`
- `STORAGE_BACKEND` — `local` | `s3` (R2/MinIO/AWS via `django-storages`)
- `SENTRY_DSN` — enable error/perf tracking in prod

---

## 5. Production

### 5.1 Process model

Run these as separate, independently-scaled deployments off the **same image**:

| Process | Command |
|---------|---------|
| Web (ASGI) | `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers $WEB_CONCURRENCY` |
| Celery worker | `celery -A config worker -l info -Q documents,ai,automation,celery` |
| Celery beat | `celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler` |

Put **nginx / a cloud load balancer** in front for TLS termination and to
proxy both HTTP and `Upgrade: websocket` traffic to the ASGI app.

### 5.2 Managed Postgres (RDS / Cloud SQL / Neon / Supabase)

Most managed Postgres support pgvector but disallow `CREATE EXTENSION` from app
roles. Pre-create it once as an admin:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Then run `python manage.py migrate` (the extension migration becomes a no-op).

### 5.3 Static & media

```bash
COLLECT_STATIC=true   # entrypoint runs collectstatic
```

Static files are served by WhiteNoise. For media (uploads) in production set
`STORAGE_BACKEND=s3` and configure the `AWS_*` variables (works with AWS S3,
Cloudflare R2, or MinIO).

### 5.4 Security checklist (handled by `config.settings.prod`)

- `DEBUG=False`, HSTS, secure cookies, SSL redirect, nosniff, `X-Frame-Options: DENY`
- JWT access/refresh with rotation + blacklist on logout
- Per-user/anon API throttling
- Object-level permissions for multi-tenant isolation
- Run `python manage.py check --deploy` before shipping

### 5.5 Scaling notes

- Heavy AI/embedding work runs on the `ai`/`documents` queues — scale those
  workers independently from quick `automation`/`celery` tasks.
- `CELERY_WORKER_PREFETCH_MULTIPLIER=1` ensures long LLM tasks don't block.
- The Channels layer uses Redis, so WebSocket fan-out works across many web
  replicas.
- For very large vector corpora, migrate `VECTOR_BACKEND` to a dedicated store
  (Pinecone/Weaviate) by implementing the adapter in
  `apps/ai_engine/services/vector_store.py` — no caller changes needed.

---

## 6. Kubernetes (sketch)

Deploy three `Deployment`s (web/worker/beat) from the same image, a `Service` +
`Ingress` (with WebSocket annotations) for web, and use managed Postgres+Redis
or in-cluster operators. Mount secrets as env vars. Liveness/readiness probes
should hit `/health/`.
