# Viva questions and concise answers

1. **What is RAG?** A retriever selects external evidence for a query, and a generator uses that evidence while answering. It helps update knowledge without retraining a model; it does not automatically guarantee truth.
2. **Why multimodal?** Relevant facts may live in tables, scans, images, speech, video, or logs, so a text-only upload path misses evidence.
3. **What is the novelty claim?** The project integrates source-located representations and owner-scoped hybrid retrieval across formats. Novel algorithmic improvement has not been established; that requires literature review and controlled evaluation.
4. **What is a chunk?** A searchable passage with text, file ID, owner, modality, order, and a source location such as page or timestamp.
5. **Why preserve tables?** Splitting a row away from its header can make values ambiguous and cause wrong answers.
6. **How is a scanned PDF handled?** PyMuPDF detects sparse page text, renders the page, and Tesseract OCR extracts visible text. Extraction can fail on low-quality scans.
7. **How are images indexed?** OCR text and optional BLIP captions enter the text index; optional CLIP image vectors enter a separate visual index.
8. **What is CLIP?** A dual-encoder model mapping images and text into a comparable embedding space for cross-modal retrieval.
9. **What is BLIP used for?** Producing a short image caption that supplements OCR. The caption can omit details or hallucinate.
10. **How is audio processed?** faster-whisper transcribes speech and stores text chunks with start/end timestamps.
11. **How is video processed?** OpenCV samples frames and selects visibly changed keyframes; FFmpeg extracts audio for transcription.
12. **Can the platform read exact chart values?** It can OCR labels and describe images, but arbitrary chart values are not reliably reconstructed in this version.
13. **What does BM25 add?** Exact term and rare-keyword matching, useful for codes, names, and technical terms that dense retrieval may miss.
14. **What do dense embeddings add?** They can surface semantically related wording even if the query lacks an exact keyword, depending on the model.
15. **How are BM25 and vector ranks combined?** Reciprocal-rank fusion sums weighted reciprocal ranks, reducing dependence on incomparable raw scores.
16. **What is reranking?** A cross-encoder scores the query and candidate passage jointly after fast candidate retrieval, at additional latency.
17. **What is semantic chunking?** Sentence embeddings indicate when adjacent sentences are less related; boundaries are placed near those changes and size limits.
18. **What does top-k control?** How many passages are supplied to an answer. Too few can omit facts; too many can increase noise, cost, and latency.
19. **How are multiple files combined?** Retrieval selects chunks from all allowed files. The prompt can ask the model to compare cited facts, but multi-hop correctness still needs evaluation.
20. **What is a citation here?** A numbered link between an answer and a retrieved chunk, carrying file and location metadata. The backend checks reference numbers, not entailment.
21. **What is the confidence score?** A heuristic label based on retrieval similarity/result count, not a calibrated probability. It should not be treated as factual certainty.
22. **What happens when no evidence is found?** The answer explicitly says it could not find relevant source evidence.
23. **How do you reduce prompt injection?** Source text is framed as untrusted data in a system instruction, and citation identifiers are checked. Stronger content isolation and adversarial tests remain necessary.
24. **Why use PostgreSQL and SQLite?** PostgreSQL supports concurrent deployment; SQLite simplifies isolated local demonstration and tests.
25. **Why a vector database?** It indexes embeddings for nearest-neighbor retrieval with owner/file payload filters. SQL stores authoritative ownership and metadata.
26. **Why provide FAISS, Chroma, and Qdrant?** They serve different local and scalable use cases. The FAISS implementation currently rebuilds per-tenant flat indexes from SQL; Qdrant server is preferred for scale.
27. **How are files isolated?** Owner ID is checked in SQL routes and vector payload filters, with final result rows joined back to owner-scoped SQL chunks.
28. **Can an admin preview another user's file?** No. Admin endpoints expose account metadata and aggregate events, while the preview route requires ownership.
29. **What are access and refresh tokens?** Short-lived access JWTs authenticate requests; longer-lived refresh JWTs rotate and can be revoked server-side.
30. **Why is the refresh token design still a risk?** Session storage is readable by injected browser script. Public deployment should use HttpOnly secure cookies, CSRF protection, and CSP.
31. **Why Celery and Redis?** Processing OCR/media/embeddings can outlast an HTTP request; a queue lets workers run separately and retry transient failures.
32. **Is indexing perfectly crash-safe?** No. SQL and vector writes are separate; a crash can leave inconsistent index state requiring reconciliation.
33. **What does the log anomaly summarizer do?** It counts error-like values and uses a median/median-absolute-deviation heuristic on numeric fields. It is not a trained anomaly model.
34. **How do you measure retrieval?** Annotate relevant evidence and compute Recall@k, MRR, nDCG, and modality-specific failure rates.
35. **How do you measure answer quality?** Compare atomic answer facts and citations with independently annotated source evidence; measure abstention on unanswerable questions.
36. **What is an ablation study?** Change one pipeline component at a time, such as removing OCR or reranking, to estimate its contribution under the same benchmark.
37. **Why use extractive mode?** It provides an offline baseline that quotes relevant passages with citations and avoids depending on a generation API.
38. **Does the current test suite prove enterprise readiness?** No. It validates focused workflows; security review, load testing, model quality evaluation, and operational controls remain.
39. **How would you improve multilingual retrieval?** Install language-specific OCR packs, use a multilingual embedding model, label multilingual queries, and measure per-language results.
40. **What would you implement next?** A consented labeled benchmark and systematic error analysis, followed by the change that addresses the largest measured failure category.
