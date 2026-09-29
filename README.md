# Atlas — Enterprise Multi-Modal Document Intelligence

A final-year project implementation of private multimodal retrieval-augmented search and question answering. Atlas ingests documents, scans, images, spreadsheets, recordings, video, and logs; stores source-located chunks; retrieves with lexical and vector signals; and returns cited answers. The repository was initialized from the existing `Yashovardhan47/AI-muti_model_rag` license-only project.

## What runs today

- React 19, TypeScript, Vite 8, Tailwind 4, Material UI, React Query, Axios, Zustand, Recharts, and Framer Motion UI.
- FastAPI, SQLAlchemy, Alembic, PostgreSQL or SQLite, JWT access and rotating refresh tokens, bcrypt, user/admin roles, owner-scoped files, upload limits and format validation, rate limits, audit events, and exports.
- Parsers for PDF, DOCX, PPTX, XLSX/CSV, TXT, JSON/JSONL logs, images, MP3/WAV/M4A, and MP4/MOV. Scanned PDF pages and pictures use OCR. Whisper transcribes audio and video soundtracks; OpenCV selects video frames. Tables retain row context. Optional BLIP captions, CLIP image vectors, Camelot tables, PaddleOCR, and unstructured fallback require their models or extra dependencies.
- Document-aware, fixed, recursive, and semantic chunking; BM25 plus dense vector retrieval; optional cross-encoder reranking; file, owner, type, date, and tag search filters; Qdrant, Chroma, or FAISS selection.
- OpenAI, Anthropic, Ollama (Llama 3/Mistral/Phi model selection), or evidence-only extractive answering. SSE supports provider token streaming and a validated final answer with citations.
- Dashboard, uploads, chat history, search, reports, and admin analytics. Source files remain downloadable only by their owners. Local hash embeddings are offered explicitly for a no-download demonstration, with lower semantic quality.

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
│   │   ├── services/     format extraction, processing
│   │   ├── rag/          chunking, embeddings, vector index, retrieval, LLMs
│   │   ├── workers/      Celery task
│   │   └── utils/        reserved for shared utilities
│   ├── alembic/versions/0001_initial.py
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
| `POST /files/upload`; `GET /files/list`, `/files/{id}/preview`; `PATCH /files/{id}/tags`; `POST /files/{id}/process`, `/files/process`; `DELETE /files/{id}` | Source lifecycle |
| `POST /chat/query`, `/chat/query/stream`; `GET /chat/history`, `/chat/history/{id}` | Answers and sessions |
| `GET /search`, `/dashboard` | Scoped retrieval and usage |
| `GET /admin/users`, `/admin/analytics`; `PATCH /admin/users/{id}/role` | Admin only |
| `GET /reports/export?format=pdf|csv|json`, `GET /health`, `GET /health/ready` | Exports and liveness |

## Configurations and limitations

- `EMBEDDING_PROVIDER=bge|e5|sentence-transformers|openai|hash`; `VECTOR_BACKEND=qdrant|chroma|faiss`; `LLM_PROVIDER=extractive|openai|anthropic|ollama`. Set compatible model names and credentials. Reindex after changing embedding dimension or model. Qdrant local mode is single-process; use its server for multiple workers.
- `ENABLE_CLIP=true` enables image/text dual-encoder indexing. `ENABLE_IMAGE_CAPTION=true` enables BLIP captions. Both download models and need substantial RAM. Text OCR works without them. Chart interpretation is OCR plus caption-based; it does not reliably recover numerical series from arbitrary plots.
- `OCR_LANG=eng+hin+tel` requires installed Tesseract language packs. Whisper can transcribe multilingual speech with the selected model. Default English BGE embedding is not tuned for every language; select a multilingual model for production evaluation.
- `WHISPER_MODEL=medium` is the default; `large-v3` improves some cases but increases RAM, download, and latency. Tesseract and FFmpeg are system packages.
- The displayed confidence label is a heuristic based on similarity and result count, **not a calibrated probability**. Citations are syntactically checked, not factually entailed. Human review is necessary for legal, medical, financial, or safety decisions.
- No benchmark results, cloud deployment, security certification, high-load test, speaker diarization, speech input, or scheduled summarization are claimed in this version. See the report for evaluation design and remaining engineering work.

## Research starting points

- Lewis et al., [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401), 2020.
- Radford et al., [Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020), 2021.
- Li et al., [BLIP: Bootstrapping Language-Image Pre-training](https://arxiv.org/abs/2201.12086), 2022.
- Radford et al., [Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356), 2022.
