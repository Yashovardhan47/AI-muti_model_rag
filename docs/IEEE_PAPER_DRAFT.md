# IEEE-style research paper draft

**Title:** Source-Aware Hybrid Retrieval for Multi-Modal Enterprise Document Question Answering

**Authors:** To be set by the student and supervisor before submission.
**Status:** Methods and experimental design draft. Results, significance tests, and claims of novelty require a completed evaluation.

## Abstract

Enterprise evidence is distributed across text, slides, tables, scans, images, audio, video, and logs. A retrieval-augmented question-answering system must preserve the location of extracted evidence, retrieve across formats, and show users what supports each answer. This paper presents Atlas, a modular prototype that normalizes heterogeneous inputs into source-located chunks, combines BM25 and dense retrieval with reciprocal-rank fusion, optionally retrieves images through CLIP, and produces answers with inspectable citations. The system includes owner-scoped indexing, an optional reranker, an extractive baseline, and cloud/local generation adapters. We describe a benchmark protocol for measuring retrieval recall, citation correctness, factual support, abstention, latency, and cost across modalities. Implementation tests verify key workflows and access isolation; quantitative quality outcomes will be reported after a labeled benchmark is completed.

**Index Terms—** retrieval-augmented generation, multimodal retrieval, enterprise search, provenance, document understanding.

## I. Introduction

Documents and media in enterprises have heterogeneous structures. OCR, ASR, and image captioning expose some of their content to text search, but a flattened transcript can lose page, slide, row, and time context. RAG [1] motivates a retriever plus a generator with explicit evidence. Our engineering goal is a source-aware pipeline where the user can open the original item from a cited chunk, including across mixed modalities. The scientific question is whether source-aware hybrid retrieval yields stronger evidence retrieval and supported answers than lexical or dense-only baselines on cross-format questions.

**Contributions proposed for evaluation:** (1) one source-located representation across document, tabular, image, audio, video, and log segments; (2) an owner-scoped hybrid retrieval pipeline with optional visual retrieval and reranking; (3) a reproducible benchmark and ablation plan for provenance and factual support. These are system contributions; no state-of-the-art or unique-algorithm claim is made before prior-work review and measurement.

## II. Related Work

Lewis et al. [1] introduced retrieval-augmented generation for knowledge-intensive NLP. CLIP [2] offers aligned image and text embeddings; BLIP [3] supports image captioning; Whisper [4] supplies multilingual speech recognition. Atlas uses these as replaceable components, rather than training a new foundation model. A final submission should extend this section with a systematic review of recent multimodal RAG, document layout, chart QA, multimodal benchmark, and provenance verification work, citing original papers and distinguishing each research gap precisely.

## III. System and Method

A file $f$ becomes segments $s_i=(x_i,m_i,\ell_i,f,u)$ where $x_i$ is extracted text, $m_i$ is modality, $\ell_i$ is source location, and $u$ is owner. Each segment is chunked without breaking short table units. Text embeddings $e_i=E(x_i)$ are stored with owner and file metadata; optional image vectors use CLIP in a separate index. The lexical retriever computes BM25; the dense retriever returns nearest indexed embeddings. For each candidate $d$, reciprocal-rank fusion computes

$$R(d)=\frac{w_b}{k_0+r_b(d)}+\frac{w_v}{k_0+r_v(d)},$$

where $w_b=0.35$, $w_v=0.65$, and $k_0=60$ in the initial implementation. A CLIP candidate receives an additional visual rank term when enabled. The values are initial engineering choices and will be tuned only on a development split. An optional cross-encoder rescoring stage reorders candidate pairs $(q,d)$.

At generation time, $q$ and numbered excerpts $[1]\ldots[k]$ enter a provider-independent prompt instructing the model to use only source evidence and to cite claims. The backend rejects unknown citation identifiers and substitutes direct source excerpts if the answer lacks valid identifiers. Citation-number checking does not prove semantic entailment; supportedness requires human or separately validated automatic evaluation. Conversations store recent turns, but retrieval always uses owner-scoped files.

## IV. Experimental Design

**Dataset:** Redacted and permission-cleared files, stratified by format, scan quality, language, size, and answerability. Annotators independently label relevant chunks, answer facts, and source locations; disagreements are adjudicated blind to system output. Aim for at least 200 questions across 100+ sources with a held-out set by document family or source organization.

**Baselines:** BM25 only, dense only, hybrid, hybrid + reranker, and hybrid + optional OCR/caption/CLIP. Also compare chunking modes and $k\in\{3,5,10,20\}$. Keep the same corpus, query split, model revision, and answer prompt for controlled comparisons.

**Metrics:** Recall@k, MRR@10, nDCG@10, citation precision/recall, atomic fact support rate, correct abstention on unanswerable questions, p50/p95 retrieval/end-to-end latency, storage bytes per source, and API cost where applicable. Bootstrap confidence intervals by question, report per-modality slices, and review errors in OCR, ASR, charts, retrieval, reasoning, and citations. Privacy canaries must never cross owners.

## V. Implementation and Preliminary Verification

Atlas consists of a React/TypeScript client and FastAPI application, SQLAlchemy/Alembic metadata, selectable vector stores, Redis/Celery processing, and provider adapters. A focused test suite currently exercises registration, authentication boundaries, owner isolation, ingest/search/chat, SSE output, duplicate handling, and deletion. A frontend production build passes. These tests are functional checks only; this draft intentionally has no invented retrieval or answer-quality figures.

## VI. Threats to Validity

An extracted table can exceed chunk limits; OCR/ASR quality depends on input conditions and installed model/language packs; captions can omit numerical chart features; LLMs can attach valid citation numbers to false claims; the proposed benchmark may not represent regulated or high-volume enterprise deployments. Annotator agreement, de-identification, provider revision pinning, and per-modality error analyses are necessary before drawing general conclusions.

## VII. Conclusion

The implemented prototype provides a concrete source-aware multimodal RAG architecture and a controlled path to measure whether hybrid retrieval improves evidence discovery. Publication claims should be written only after the benchmark, ablations, and statistical reporting are complete.

## References

[1] P. Lewis et al., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,” NeurIPS, 2020. https://arxiv.org/abs/2005.11401
[2] A. Radford et al., “Learning Transferable Visual Models From Natural Language Supervision,” ICML, 2021. https://arxiv.org/abs/2103.00020
[3] J. Li et al., “BLIP: Bootstrapping Language-Image Pre-training for Unified Vision-Language Understanding and Generation,” ICML, 2022. https://arxiv.org/abs/2201.12086
[4] A. Radford et al., “Robust Speech Recognition via Large-Scale Weak Supervision,” 2022. https://arxiv.org/abs/2212.04356
