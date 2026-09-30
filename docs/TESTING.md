# Testing and evaluation guide

## Automated checks

From repository root after installing backend and frontend dependencies:

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
python -m compileall -q backend/app backend/alembic
cd frontend && npm ci && npm run build
```

The integration tests use isolated temporary SQLite and local Qdrant paths plus explicit hash/extractive mode. They verify registration, refresh rotation, logout, tenant isolation, upload/duplicate handling, indexing, hybrid search, citations, chat history, streamed output, tags, and deletion. They do not prove that every media decoder or external provider works.

## Manual acceptance walkthrough

1. Create two ordinary users. Upload a TXT containing a unique fact as user A. Confirm status `ready` and that A can find/cite it; B cannot list, preview, select, search, or read A's session.
2. Upload PDF with searchable text, a scanned PDF, DOCX with tables, PPTX with a chart image, XLSX and CSV, JSONL sensor logs, a PNG chart, an audio recording, and a short MP4. For each, verify status and that location metadata identifies page/slide/row/time. Install Tesseract, FFmpeg, Whisper weights, and optional model dependencies as configured.
3. Submit a question requiring two files. Check every answer claim against the linked source. Test absent evidence; expect an explicit inability to verify.
4. Try invalid extension, mislabeled PDF, empty file, oversized file, duplicate, unsupported password-protected document, and corrupted audio. Check 4xx rejection or visible failed state and retry.
5. Verify type/date/tag filters, upload/process/delete, reports, history, light/dark layout, mobile navigation, and admin-only routes. Run PostgreSQL + Redis + Qdrant Compose separately from SQLite smoke tests.
6. Verify provider credentials and Ollama availability when enabling generation. Audit latency and usage costs. Test reconnection, worker restart, queue outage, and deletion during indexing before public deployment.

## Research evaluation protocol

Build a consented, redacted benchmark with at least 100 documents distributed across 10+ format/language classes and 200+ human-authored questions. Annotate each question with relevant chunk IDs, expected answer facts, allowed citations, and an `unanswerable` label where appropriate. Split documents by source organization or collection to prevent leakage. Keep the benchmark, model revisions, prompts, and settings versioned.

Compare: (A) BM25, (B) dense retrieval, (C) reciprocal-rank-fused hybrid, and (D) hybrid plus cross-encoder. Then ablate OCR, captions, CLIP, chunking strategy, and top-k. Report Recall@5/10, MRR@10, nDCG@10 by modality, citation precision/recall, answer factuality judged blind against gold evidence, abstention precision on unanswerable queries, p50/p95 latency, index time, storage growth, and approximate cost per 100 queries. Show bootstrap 95% confidence intervals by query and breakdowns by scan quality, chart type, language, and document length. Do not report a higher recall or accuracy claim until those measurements exist.

For privacy test that no answer or citation contains a canary from another user's tenant across all API paths and vector backends. For prompt injection test source text containing instructions like “ignore previous instructions”; assert it is quoted as data or rejected, never followed. For corruption test kill a worker between vector and SQL commit and inspect recovery needs.

## Current checked result

At initial implementation the focused backend integration suite completed with 4 passing tests, and the frontend TypeScript/Vite production build succeeded. These are implementation smoke checks, not retrieval-quality or security certification. Re-run on the exact branch commit before demonstration.
