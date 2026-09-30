# Deployment and operations

## Local SQLite route

1. Install Python 3.11+ / Node 22.12+, Tesseract, FFmpeg; copy `.env.example` to `.env` at repository root and replace the secret.
2. Choose `EMBEDDING_PROVIDER=hash` for a deterministic offline smoke test or use BGE to download a semantic encoder. Set `LLM_PROVIDER=extractive` for evidence-only mode. Run `pip install -r backend/requirements.txt` in a virtual environment.
3. From `backend/`, create `data/`, run `alembic upgrade head`, and run `uvicorn app.main:app --host 127.0.0.1 --port 8000`.
4. From `frontend/`, run `npm ci && npm run dev`. Visit `http://localhost:5173`.
5. To run a Celery queue, start Redis, set `REDIS_URL`, and run `celery -A app.workers.tasks.celery_app worker --loglevel=info` from `backend/`. Use remote Qdrant when more than one process may write vectors.

Windows PowerShell equivalents: `py -3.12 -m venv .venv`, `.venv\Scripts\Activate.ps1`, `New-Item -ItemType Directory -Force backend\data`. Docker Desktop can supply Tesseract and FFmpeg without local installation.

## Docker Compose route

Set `POSTGRES_PASSWORD`, `JWT_SECRET`, `CORS_ORIGINS`, and optionally `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env`. Run `docker compose up --build` and then `docker compose ps`. The frontend is served at port 5173, API at port 8000. For a real deployment remove direct public database, Redis, Qdrant, and API exposure, replace HTTP with HTTPS through a proxy, and set the public frontend origin exactly. Set `APP_ENV=production` to reject the example JWT secret. Pin model revisions and container digests before a reproducible release.

Persistent Compose volumes: PostgreSQL `pg_data`, Redis `redis_data`, Qdrant `qdrant_data`, and uploaded blobs `uploads`. Back up all four together and verify restore. Keep `.env` outside version control. During updates run `alembic upgrade head` before starting API/worker; the container API command does this. For rollback, restore matching DB/index/storage snapshots rather than assuming a downgrade will preserve data.

## Processing and model options

| Setting | Values | Notes |
| --- | --- | --- |
| `DATABASE_URL` | SQLite / `postgresql+psycopg://...` | SQLite is a single-user demo choice; Postgres supports concurrency. |
| `EMBEDDING_PROVIDER` | `bge`, `e5`, `sentence-transformers`, `openai`, `hash` | Hash is low-quality offline mode. Model change requires reindex. |
| `VECTOR_BACKEND` | `qdrant`, `chroma`, `faiss` | FAISS rebuilds a per-user flat index from SQL vectors at query time; use Qdrant server for scale. |
| `LLM_PROVIDER` | `extractive`, `openai`, `anthropic`, `ollama` | Local Ollama requires pulling a model such as `llama3`, `mistral`, or `phi3`. |
| `ENABLE_CLIP` / `ENABLE_IMAGE_CAPTION` | boolean | Optional image model downloads. |
| `OCR_ENGINE` | `tesseract`, `paddle` | PaddleOCR 2.x is an optional dependency. |
| `PDF_TABLE_ENGINE` | `pdfplumber`, `camelot` | Camelot and system dependencies are optional. |
| `OCR_LANG` | `eng`, `eng+hin+tel` | Install relevant Tesseract language packs. |
| `UNSTRUCTURED_FALLBACK` | boolean | Optional unstructured partitioning on empty PDF/DOCX extraction. |

## Security and reliability work before external access

The repository includes ownership checks on file, session, search, and vector queries; strict CORS allowlist; upload size and signature checks; 30-minute access tokens and rotating 14-day refresh tokens; RBAC; audit events; and rate limiting. Refresh tokens are stored in the browser's session storage, so a browser script injection could steal them. Public hosting should switch to secure HttpOnly cookies with CSRF defenses, enforce CSP and HTTPS, place a WAF and malware scanner on uploads, sandbox document parsing, limit OCR/video CPU time and decompressed file size, add per-user storage and cost quotas, and rotate all keys. Review PDF and media decoders for security patches. Redis availability is required when configured for distributed rate limiting and background tasks.

The file/index write is not an atomic distributed transaction; a worker crash can leave an orphan vector or a failed file requiring reprocess. Production operation needs reconciliation, dead-letter handling, an outbox or idempotent job state, vector index rebuild tooling, task monitoring, and load tests. `/health` is liveness and `/health/ready` checks SQL, configured Redis, and vector service. Add model-provider readiness and managed probes before deployment. Use a privacy agreement before sending confidential source text to cloud LLM or embedding APIs.
