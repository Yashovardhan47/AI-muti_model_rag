# Atlas — Enterprise Multi-Modal Document Intelligence

A final-year project implementation of private multimodal retrieval-augmented search and question answering. Atlas ingests documents, scans, images, spreadsheets, recordings, video, and logs; stores source-located chunks; retrieves with lexical and vector signals; and returns cited answers. The repository was initialized from the existing `Yashovardhan47/AI-muti_model_rag` license-only project.

## What runs today

- React 19, TypeScript, Vite 8, Tailwind 4, Material UI, React Query, Axios, Zustand, Recharts, and Framer Motion UI.
- FastAPI, SQLAlchemy, Alembic, PostgreSQL or SQLite, JWT access and rotating refresh tokens, bcrypt, user/admin roles, owner-scoped files, upload limits and format validation, rate limits, audit events, and exports.
- Parsers for PDF, DOCX, PPTX, XLSX/CSV, TXT, JSON/JSONL logs, images, MP3/WAV/M4A, and MP4/MOV. Scanned PDF pages and pictures use OCR. Whisper transcribes audio and video soundtracks; OpenCV selects video frames. Tables retain row context. Optional BLIP captions, CLIP image vectors, Camelot tables, PaddleOCR, and unstructured fallback require their models or extra dependencies.
- Document-aware, fixed, recursive, and semantic chunking; BM25 plus dense vector retrieval; optional cross-encoder reranking; file, owner, type, date, and tag search filters; Qdrant, Chroma, or FAISS selection.
- OpenAI, Anthropic, Ollama (Llama 3/Mistral/Phi model selection), or evidence-only extractive answering. SSE delivers audited answer chunks and a final answer with citations.
- An evidence audit checks claim-level citation IDs and exact numbers before a generated answer is shown. Numbers supported only by OCR, generated captions, or speech recognition are withheld as unverified. A failed draft is replaced with direct passages. Citations include source version digest, locator, and extraction signals. See [novelty roadmap](docs/NOVELTY_ROADMAP.md) for precise claims and limits.
- Source revisions remain addressable; current-version search is the default, while historical versions can be searched explicitly. Exact parsed table/log field changes and changed passages can be compared. The evidence viewer renders PDF pages and visual regions or seeks to a cited audio/video time. Visual highlighting can be approximate.
- Owner-issued read grants cover a source's versions. Shared users can search and cite, but cannot modify files; deletion or revocation redacts their stored cited answers. An hourly index reconciliation task replays committed vectors and queues interrupted work. A folder sync CLI uploads changed local files as new revisions.
- English, Hindi, and Telugu OCR selection and answer-language prompts are supported, with multilingual E5 as an embedding option. A synthetic ten-question benchmark seed and evaluation harness report retrieval recall/MRR, structural abstention, and latency by modality/language. These are not validated quality results.
- Dashboard, uploads, chat history, search, reports, and admin analytics. Local hash embeddings are offered explicitly for a no-download demonstration, with lower semantic quality.

## Quick start: offline demo

Prerequisites: Python 3.11+ (3.12 tested), Node 22.12+, npm, Tesseract, FFmpeg. The first `pip install` can be large because local ML support includes PyTorch. In a terminal at the repository root:

```bash
cp .env.example .env
# Generate a secret and replace JWT_SECRET in .env before sharing this instance.
python -m venv .venv
. .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd backend
mkdir -p data                 # Windows PowerShell: New-Item -ItemType Directory -Force data
alembic upgrade head
```

For an offline, low-resource demo set `EMBEDDING_PROVIDER=hash` in `.env`. This uses deterministic lexical hash vectors, **not** a semantic model. Keep `LLM_PROVIDER=extractive` for direct cited passages. For semantic retrieval keep the default BGE model, which downloads weights on first indexing/query. Run the API from `backend/`:

```bash
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`; the API docs are at `http://localhost:8000/docs`. Register, upload a TXT or PDF, wait until status becomes `ready`, then search and ask a question. Local indexing uses a FastAPI background task after the upload response; start Redis/Celery for durable queue operation.

## Browser preview deployment

[Deploy your own browser preview on Render](https://render.com/deploy?repo=https://github.com/Yashovardhan47/AI-muti_model_rag). This opens the hosting setup; it is not a live demo URL until the deployment completes.

The repository includes a single-service [Render Blueprint](render.yaml) and [preview Dockerfile](Dockerfile.demo). Connect this GitHub repository in Render and create a Blueprint instance to receive a live URL. The same origin serves React at `/` and FastAPI at `/api` (API docs at `/api/docs`). The container initializes the database and shows a temporary-data notice; visitors register their own accounts and can upload sample documents, search, chat, and inspect citations.

The free preview uses hash embeddings, extractive answers, a tiny speech model, SQLite, local Qdrant, and FastAPI background processing. Model-heavy capabilities and concurrent workloads need a larger service. Free instance storage is ephemeral, so accounts and uploads can disappear on restart; do not submit private material. This Blueprint is for browsing the project, not a persistent enterprise deployment. See [deployment](docs/DEPLOYMENT.md) for the full-stack Docker Compose route.

## Container mode

Copy `.env.example` to `.env`, set a unique 32+ character `JWT_SECRET`, set `POSTGRES_PASSWORD` in `.env`, and change `CORS_ORIGINS` to the actual origin. Set `EMBEDDING_PROVIDER=hash` if avoiding initial model downloads. Then run `docker compose up --build`; open `http://localhost:5173`. The API migrates PostgreSQL on startup. A Redis-backed Celery worker, seven-day embedding cache, and remote Qdrant run alongside it. For a privileged account, set `ADMIN_EMAIL` and a 12+ character `ADMIN_PASSWORD` before the first startup. Public registration always creates a User account.

**Do not deploy the Compose example directly to the public Internet.** Put a TLS reverse proxy in front, restrict service ports, set infrastructure secrets, add malware scanning and resource quotas, and complete the security review described in [deployment](docs/DEPLOYMENT.md). The working application is a research prototype with production-oriented structure, not a certified enterprise product.

## Repository layout and requested build order

```text
.
├── backend/
│   ├── app/
│   │   ├── api/          auth, files, chat, search, admin, reports
│   │   ├── core/         config, database, security, rate limiting
│   │   ├── models/       SQLAlchemy entities
│   │   ├── schemas/      Pydantic request/response models
│   │   ├── services/     extraction, access, processing, comparisons, recovery
│   │   ├── rag/          chunking, embeddings, vector index, retrieval, LLMs
│   │   ├── workers/      Celery indexing and scheduled reconciliation
│   │   └── utils/        reserved for shared utilities
│   ├── alembic/versions/0001_initial.py through 0003_source_intelligence.py
│   ├── tools/           folder sync and benchmark scripts
│   ├── benchmarks/      synthetic fixture corpus
│   ├── tests/
│   ├── requirements.txt
│   └── requirements-optional.txt
├── frontend/src/
│   ├── components/
│   ├── lib/
│   └── pages/
├── docs/
├── docker-compose.yml
└── .env.example
```

| Step | Deliverable | Location |
| --- | --- | --- |
| 1 | Folder structure | Tree above |
| 2 | Backend dependencies | `backend/requirements.txt`, optional extras |
| 3 | Backend modules and endpoints | `backend/app/` |
| 4 | Frontend pages and components | `frontend/src/` |
| 5 | Schema and migration | `backend/app/models/`, `backend/alembic/` |
| 6 | RAG pipeline | `backend/app/rag/` |
| 7 | Multimodal ingestion | `backend/app/services/` |
| 8 | Deployment guide | [DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| 9 | README | This file |
| 10 | Testing guide | [TESTING.md](docs/TESTING.md) |
| 11 | Final-year project report | [PROJECT_REPORT.md](docs/PROJECT_REPORT.md) |
| 12 | IEEE paper draft | [IEEE_PAPER_DRAFT.md](docs/IEEE_PAPER_DRAFT.md) |
| 13 | Presentation content | [PRESENTATION.md](docs/PRESENTATION.md) |
| 14 | Viva questions and answers | [VIVA.md](docs/VIVA.md) |

## API map

| Endpoint | Purpose |
| --- | --- |
| `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`; `GET /auth/me` | JWT session lifecycle |
| `POST /files/upload` (optional `replace_file_id`, `ocr_languages`); `GET /files/list`, `/files/{id}/preview`, `/files/{id}/versions`, `/files/{id}/evidence/{chunk_id}`, `/files/{id}/evidence/{chunk_id}/image`, `/files/compare`; `PATCH /files/{id}/tags`; `POST /files/{id}/process`; `DELETE /files/{id}` | Revisions, source preview, located evidence, comparison, and lifecycle |
| `GET/POST /files/{id}/access`, `DELETE /files/{id}/access/{user_id}` | Owner-managed read grants across versions |
| `POST /chat/query`, `/chat/query/stream`; `GET /chat/history`, `/chat/history/{id}` | Answers, evidence audits, and source freshness in history |
| `GET /search`, `/dashboard` | Scoped retrieval and usage |
| `GET /admin/users`, `/admin/analytics`; `PATCH /admin/users/{id}/role`; `POST /admin/reconcile` | Admin only |
| `GET /reports/export?format=pdf|csv|json`, `GET /health`, `GET /health/ready` | Exports and liveness |

## Configurations and limitations

- `EMBEDDING_PROVIDER=bge|e5|multilingual-e5|sentence-transformers|openai|hash`; `VECTOR_BACKEND=qdrant|chroma|faiss`; `LLM_PROVIDER=extractive|openai|anthropic|ollama`. Set compatible model names and credentials. Reindex after changing embedding dimension or model. Qdrant local mode is single-process; use its server for multiple workers.
- `ENABLE_CLIP=true` enables image/text dual-encoder indexing. `ENABLE_IMAGE_CAPTION=true` enables BLIP captions. Both download models and need substantial RAM. Text OCR works without them. Chart interpretation is OCR plus caption-based; it does not reliably recover numerical series from arbitrary plots.
- Select `eng`, `hin`, `tel`, or their combinations per upload. Install corresponding Tesseract language packs; the optional PaddleOCR adapter currently supports English only. Whisper can transcribe multilingual speech with the selected model. Default English BGE is not tuned for cross-language search; select `multilingual-e5` and reindex for Hindi/Telugu evaluation. Extractive mode quotes the source language and cannot translate it.
- `WHISPER_MODEL=medium` is the default; `large-v3` improves some cases but increases RAM, download, and latency. Tesseract and FFmpeg are system packages.
- Responses report `confidence=not_calibrated`. The claim audit checks citation identifiers and exact numeric presence, **not semantic entailment**. It can miss false nonnumeric claims or refuse valid computed values. Human review is necessary for legal, medical, financial, or safety decisions.
- The SSE endpoint buffers provider output until the audit completes, then sends approved text as delta events and a final event. This prevents an unchecked draft appearing in the UI, but increases time to first displayed answer.
- Version comparison identifies exact tabular differences and changed text; it does not infer semantic contradiction between paraphrases, units, or time periods. OCR boxes can cover an entire region; PDF anchors may highlight a matching phrase, or only the page if no phrase matches. The hourly reconciliation replays committed refs, but does not replace transactional storage or tested backup restore.
- History compares the saved citation digest with current file metadata and checks that the stored file exists; it does not rehash disk bytes on every history read or track external document revisions.
- Deletion redacts assistant messages that cite the file; the user's own questions and session titles remain until a future conversation-deletion control is implemented. Backups require a separate retention policy.
- No benchmark quality result, cloud deployment, security certification, high-load test, speaker diarization, speech input, or scheduled summarization is claimed in this version. See the report for evaluation design and remaining engineering work.

## Folder sync and smoke benchmark

Use an account dedicated to the watched folder. Local deletion does not delete a server source. A rotated refresh token can be stored outside the watched folder in a private file:

```bash
export ATLAS_SYNC_TOKEN='access token from /auth/login'
export ATLAS_SYNC_REFRESH_TOKEN='refresh token from /auth/login'
python backend/tools/sync_folder.py ./documents --interval 60 --refresh-token-file ~/.atlas-sync-refresh
```

For a synthetic retrieval smoke test, use a separate test account and its access token:

```bash
export ATLAS_BENCHMARK_TOKEN='test account access token'
python backend/tools/seed_benchmark.py --output benchmark-smoke.jsonl
python backend/tools/evaluate.py benchmark-smoke.jsonl --top-k 6 --output benchmark-results.json
```

The first script writes real uploaded file IDs into labels. To test answers as well, add `--answers` to the evaluation command; it records queries in the test account and can incur model cost.

## Research starting points

- Lewis et al., [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401), 2020.
- Radford et al., [Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020), 2021.
- Li et al., [BLIP: Bootstrapping Language-Image Pre-training](https://arxiv.org/abs/2201.12086), 2022.
- Radford et al., [Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356), 2022.
