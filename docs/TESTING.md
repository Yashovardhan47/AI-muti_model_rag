# Testing and evaluation guide

## Automated checks

From repository root after installing backend and frontend dependencies:

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
python -m compileall -q backend/app backend/alembic
cd frontend && npm ci && npm run build
```

The integration tests use isolated temporary SQLite and local Qdrant paths plus explicit hash/extractive mode. They verify registration, refresh rotation, logout, tenant isolation, upload/duplicate handling, indexing, hybrid search, citations, chat history, streamed output, tags, and deletion. They do not prove that every media decoder or external provider works.

For dependency-free checks of the evidence guard and evaluation arithmetic, from `backend/` run:

```bash
python -m unittest tests.test_evidence tests.test_evaluation -v
```

The integration suite additionally checks that generated unsupported numbers never appear in sync or SSE output, that the audit persists in history, and that a deleted source is marked unavailable. Run Alembic upgrade on both an existing `0001_initial` database and a clean database when preparing a deployment.

## Manual acceptance walkthrough

1. Create two ordinary users. Upload a TXT containing a unique fact as user A. Confirm status `ready` and that A can find/cite it; B cannot list, preview, select, search, or read A's session.
2. Upload PDF with searchable text, a scanned PDF, DOCX with tables, PPTX with a chart image, XLSX and CSV, JSONL sensor logs, a PNG chart, an audio recording, and a short MP4. For each, verify status and that location metadata identifies page/slide/row/time. Install Tesseract, FFmpeg, Whisper weights, and optional model dependencies as configured.
3. Submit a question requiring two files. Check every answer claim against the linked source. Test absent evidence; expect an explicit inability to verify.
4. Try invalid extension, mislabeled PDF, empty file, oversized file, duplicate, unsupported password-protected document, and corrupted audio. Check 4xx rejection or visible failed state and retry.
5. Verify type/date/tag filters, upload/process/delete, reports, history, light/dark layout, mobile navigation, and admin-only routes. Run PostgreSQL + Redis + Qdrant Compose separately from SQLite smoke tests.
6. Verify provider credentials and Ollama availability when enabling generation. Audit latency and usage costs. Test reconnection, worker restart, queue outage, and deletion during indexing before public deployment.
7. Ask a model to produce an uncited claim, a nonexistent citation, and a number missing from its cited passage. Inspect the withheld answer and audit in both ordinary chat and SSE. Delete an uploaded source, reopen the conversation, and check that the assistant answer and deleted source excerpt were redacted in history and JSON export. Also test a wrong nonnumeric claim with a valid citation to see the current guard's limitation.

## Research evaluation protocol

Build a consented, redacted benchmark with at least 100 documents distributed across 10+ format/language classes and 200+ human-authored questions. Annotate each question with relevant chunk IDs, expected answer facts, allowed citations, and an `unanswerable` label where appropriate. Split documents by source organization or collection to prevent leakage. Keep the benchmark, model revisions, prompts, and settings versioned.

Compare: (A) BM25, (B) dense retrieval, (C) reciprocal-rank-fused hybrid, and (D) hybrid plus cross-encoder. Then ablate OCR, captions, CLIP, chunking strategy, and top-k. Report Recall@5/10, MRR@10, nDCG@10 by modality, citation precision/recall, answer factuality judged blind against gold evidence, abstention precision on unanswerable queries, p50/p95 latency, index time, storage growth, and approximate cost per 100 queries. Show bootstrap 95% confidence intervals by query and breakdowns by scan quality, chart type, language, and document length. Do not report a higher recall or accuracy claim until those measurements exist.

For privacy test that no answer or citation contains a canary from another user's tenant across all API paths and vector backends. For prompt injection test source text containing instructions like “ignore previous instructions”; assert it is quoted as data or rejected, never followed. For corruption test kill a worker between vector and SQL commit and inspect recovery needs.

### Repeatable retrieval study

Create a JSONL file with one human-labeled question per line. Each row has `question`, `answerable` (boolean), `modality` (label), and `evidence` (an array of exact `file_id` and `location` pairs returned by uploads and search). Include empty evidence for genuinely unanswerable questions; keep them separate when interpreting retrieval recall. Use a dedicated test account and de-identified files.

To generate a ten-case **synthetic smoke manifest** with English, Hindi, and Telugu prompts over text, CSV, and JSON fixtures, start the API in hash/extractive mode and run:

```bash
export ATLAS_BENCHMARK_TOKEN='dedicated test-account access token'
python backend/tools/seed_benchmark.py --output benchmark-smoke.jsonl
python backend/tools/evaluate.py benchmark-smoke.jsonl --top-k 6 --output benchmark-results.json
```

The seed script uploads the fixtures, waits for indexing, and writes the actual file IDs. It intentionally does not claim representative multimodal quality. For a cross-language semantic study, choose `EMBEDDING_PROVIDER=multilingual-e5` before indexing. Install `tesseract-ocr-hin` and `tesseract-ocr-tel` to evaluate scanned Hindi/Telugu content. The manifest's unanswerable case exposes false answers in extractive mode; it is a measured failure, not a passing guardrail guarantee.

```bash
export ATLAS_BENCHMARK_TOKEN='access token for the test account'
python backend/tools/evaluate.py study.jsonl --top-k 6 --output study-results.json
python backend/tools/evaluate.py study.jsonl --top-k 6 --answers --output study-answers.json
```

The default run calls `/search` and reports gold evidence recall@k, MRR, median/p95 latency overall and by modality and language. `--answers` additionally calls `/chat/query` and reports structural abstention accuracy; it may incur cloud provider cost and writes chat history to the test account. The script does **not** compute factual accuracy or prove citation support. Human annotation and blind review are still required for the research paper. Compare settings using the same labels and document split, and record model/provider revisions with each run.

## Current checked result

Run `python -m unittest tests.test_evidence tests.test_evaluation` from `backend/` for dependency-free audit and metric checks. The full `pytest -q` integration suite covers versioned search, read grants and revocation, evidence access, exact table changes, and index replay in addition to the original auth and ingestion flows. Run `alembic upgrade head` on a fresh and a pre-0003 database, then `npm run build` in `frontend/`. Review the exact main-branch CI run before demonstration. These implementation checks do not establish retrieval quality or security certification.
