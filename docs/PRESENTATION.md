# Final-year presentation content

**Suggested duration:** 10–12 minutes plus demonstration. Use actual screenshots from the running build; do not use fabricated metric charts.

## Slide 1 — Title

Enterprise Multi-Modal Document Intelligence System using RAG
Atlas · CSE (Data Science) final-year project
Presenter and guide names can be added in the actual presentation.

**Speaker note:** “Atlas helps a user ask one evidence-based question across many file formats and inspect the original source.”

## Slide 2 — The problem

- Enterprise knowledge lives in text, scanned PDFs, slides, spreadsheets, pictures, recordings, videos, and logs.
- Keyword search misses paraphrases and visual/audio evidence.
- Uncited generated answers are difficult to trust.

**Visual:** A mixed set of source icons feeding into one question and a cited answer.

## Slide 3 — Goal and objectives

- Private ingestion and source-aware indexing.
- Hybrid lexical/vector retrieval.
- Answers with file, page/slide/row/time citations.
- Search, chat, usage, reports, and administration.
- Research evaluation of retrieval and groundedness.

## Slide 4 — Architecture

Show the architecture diagram from the project report. Explain React → FastAPI → SQL/storage and upload → worker → parsers/embeddings → Qdrant → retrieval/provider.

## Slide 5 — Multimodal ingestion

| Source | Extraction | Provenance |
| --- | --- | --- |
| PDF / Office | PyMuPDF, pdfplumber, python-docx/pptx | Page, paragraph, slide |
| Images / scans | OCR, optional BLIP/CLIP | Image or scanned page |
| Tables / logs | pandas, JSON parser, numeric summary | Sheet row range or log field |
| Audio / video | Whisper, OpenCV, FFmpeg | Timestamp and keyframe |

**Speaker note:** Chart values are not guaranteed by generic OCR/captioning.

## Slide 6 — Retrieval and answer pipeline

1. Preserve table or segment boundaries while chunking.
2. BM25 and vector search generate ranked candidates inside the user's tenant.
3. Reciprocal-rank fusion and optional cross-encoder reranking.
4. Number excerpts, prompt a chosen provider, check cited identifiers, offer source preview.

## Slide 7 — Security and isolation

- User and admin roles, bcrypt, access/rotating refresh JWTs.
- File ownership enforced for uploads, previews, searches, conversation history, and vectors.
- Byte limits, signatures, duplicate detection, rate limits, audit events.
- Public deployment additionally requires TLS, scanning, sandboxing, cookies/CSP, quotas, backups.

## Slide 8 — Product demonstration

1. Register user A and upload a PDF or TXT.
2. Watch `pending → processing → ready`.
3. Ask a question and open its cited source.
4. Search by type/tag and export a report.
5. Log in as user B and show A's file cannot be accessed.

## Slide 9 — What was verified

- Backend integration checks for auth, isolation, upload, search, chat, stream, structured logs, duplicate handling, deletion.
- TypeScript/Vite production build.
- No corpus-wide factual accuracy, security certification, or throughput figure is claimed yet.

## Slide 10 — Research design

- Build a human-labeled, redacted benchmark by modality and answerability.
- Compare BM25, dense, hybrid, hybrid + reranking; ablate OCR, captions, CLIP, chunking, and top-k.
- Metrics: Recall@k, MRR, citation precision, fact support, abstention, p95 latency, and cost.
- Report confidence intervals and failure examples, not only averages.

## Slide 11 — Limitations and next steps

- Citation identifier validity does not prove factual entailment.
- Scanned handwriting, chart numbers, and diarization remain difficult.
- Model downloads, index consistency after crashes, hardened media processing, and scaled benchmarks need work.
- Next milestone: label the evaluation set, run ablations, then improve the dominant error class.

## Slide 12 — Conclusion

Atlas is a runnable, source-aware multimodal RAG prototype with clear boundaries and a reproducible research plan. Its value is measurable evidence retrieval and inspectable answers, subject to the planned benchmark.

## Slide 13 — Questions

Suggested live backup prompts: “What does the uploaded report say about the cooling pump?” and “Which log record contains the highest pressure?” Keep the exact sample files and questions used for the demo under your own control; avoid confidential documents.
