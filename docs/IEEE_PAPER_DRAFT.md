# IEEE-style research paper draft

**Title:** Toward Version-Aware Evidence Integrity in Multimodal Enterprise Retrieval-Augmented Generation

**Authors:** To be set by the student and supervisor before submission.
**Status:** Methods and experimental design draft. Results, significance tests, and claims of novelty require a completed evaluation.

## Abstract

Enterprise evidence is distributed across text, slides, tables, scans, images, audio, video, and logs. A retrieval-augmented question-answering system must preserve the location and revision of extracted evidence, retrieve across formats, and expose limits of its answers. This paper presents Atlas, a modular prototype that normalizes heterogeneous inputs into source-located chunks, combines BM25 and dense retrieval with reciprocal-rank fusion, and optionally retrieves images through CLIP. An initial evidence audit binds answer citations to source digests, checks citation identifiers and exact numbers before delivery, and marks removed or changed sources in conversation history. We describe a protocol for measuring retrieval recall, factual support, abstention, stale-source detection, latency, and cost across modalities. Implementation tests cover focused guard behavior; quantitative outcomes will be reported after a labeled benchmark is completed.

**Index Terms—** retrieval-augmented generation, multimodal retrieval, enterprise search, provenance, document understanding.

## I. Introduction

Documents and media in enterprises have heterogeneous structures. OCR, ASR, and image captioning expose some of their content to text search, but a flattened transcript can lose page, slide, row, and time context. RAG [1] motivates a retriever plus a generator with explicit evidence. Our engineering goal is a source-aware pipeline where the user can open the original item from a cited chunk, including across mixed modalities. The scientific question is whether source-aware hybrid retrieval yields stronger evidence retrieval and supported answers than lexical or dense-only baselines on cross-format questions.

**Contributions proposed for evaluation:** (1) a source-located representation across document, tabular, image, audio, video, and log segments; (2) an owner-scoped hybrid retrieval pipeline; (3) an initial version-aware citation and numeric audit with a conservative withholding policy; and (4) a reproducible benchmark plan for provenance and factual support. These are system contributions. The current audit does not verify semantic entailment; a full claim-to-region evidence graph remains future work. No state-of-the-art or unique-algorithm claim is made before measurement.

## II. Related Work

Lewis et al. [1] introduced retrieval-augmented generation for knowledge-intensive NLP. CLIP [2] offers aligned image and text embeddings; BLIP [3] supports image captioning; Whisper [4] supplies multilingual speech recognition. RAGBench [5] and CRAG [6] motivate explicit support and answerability evaluation. MMDocRAG [7] already evaluates cross-page, cross-modal evidence, while VISA [8] studies exact visual source attribution. Atlas uses replaceable components rather than training a new foundation model. A final submission must compare methods and datasets rigorously before claiming novelty.

## III. System and Method

A file $f$ becomes segments $s_i=(x_i,m_i,\ell_i,f,u)$ where $x_i$ is extracted text, $m_i$ is modality, $\ell_i$ is source location, and $u$ is owner. Each segment is chunked without breaking short table units. Text embeddings $e_i=E(x_i)$ are stored with owner and file metadata; optional image vectors use CLIP in a separate index. The lexical retriever computes BM25; the dense retriever returns nearest indexed embeddings. For each candidate $d$, reciprocal-rank fusion computes

$$R(d)=\frac{w_b}{k_0+r_b(d)}+\frac{w_v}{k_0+r_v(d)},$$

where $w_b=0.35$, $w_v=0.65$, and $k_0=60$ in the initial implementation. A CLIP candidate receives an additional visual rank term when enabled. The values are initial engineering choices and will be tuned only on a development split. An optional cross-encoder rescoring stage reorders candidate pairs $(q,d)$.

At generation time, $q$ and numbered excerpts $[1]\ldots[k]$ enter a provider-independent prompt instructing the model to use only source evidence and to cite claims. Each citation includes the uploaded file's SHA-256 and a page, row, slide, or time location. Before text is sent to the client, a deterministic audit checks that each generated sentence has a known citation and that every exact numeric value appears in its cited excerpts. A failed draft is withheld and direct passages are shown. History checks whether cited file revisions are still accessible. Citation and number checks do not prove semantic entailment, and legitimate computed answers can be withheld. Supportedness requires human or separately validated evaluation. Conversations store recent turns, but retrieval always uses owner-scoped files.

## IV. Experimental Design

**Dataset:** Redacted and permission-cleared files, stratified by format, scan quality, language, size, and answerability. Annotators independently label relevant chunks, answer facts, and source locations; disagreements are adjudicated blind to system output. Aim for at least 200 questions across 100+ sources with a held-out set by document family or source organization.

**Baselines:** BM25 only, dense only, hybrid, hybrid + reranker, and hybrid + optional OCR/caption/CLIP. Also compare chunking modes and $k\in\{3,5,10,20\}$. Keep the same corpus, query split, model revision, and answer prompt for controlled comparisons.

**Metrics:** Recall@k, MRR@10, nDCG@10, human-judged citation precision/recall, atomic fact support rate, correct abstention on unanswerable questions, stale-citation detection, false refusals, p50/p95 retrieval/end-to-end latency, storage bytes per source, and API cost where applicable. The included JSONL harness measures retrieval recall/MRR and optional abstention; it is not a fact-support judge. Bootstrap confidence intervals by question, report per-modality slices, and review errors in OCR, ASR, charts, retrieval, reasoning, and citations. Privacy canaries must never cross owners.

## V. Implementation and Preliminary Verification

Atlas consists of a React/TypeScript client and FastAPI application, SQLAlchemy/Alembic metadata, selectable vector stores, Redis/Celery processing, and provider adapters. Earlier focused integration checks exercised registration, authentication boundaries, owner isolation, ingest/search/chat, SSE output, duplicate handling, and deletion. The evidence guard and evaluation arithmetic have dependency-free unit tests. The frontend production build passed for the initial baseline and must be repeated after these changes. These are functional checks only; this draft intentionally has no invented retrieval or answer-quality figures.

## VI. Threats to Validity

An extracted table can exceed chunk limits; OCR/ASR quality depends on input conditions and installed model/language packs; captions can omit numerical chart features; LLMs can attach valid citation numbers to false claims; the proposed benchmark may not represent regulated or high-volume enterprise deployments. Annotator agreement, de-identification, provider revision pinning, and per-modality error analyses are necessary before drawing general conclusions.

## VII. Conclusion

The implemented prototype provides a concrete source-aware multimodal RAG architecture and a controlled path to measure whether hybrid retrieval improves evidence discovery. Publication claims should be written only after the benchmark, ablations, and statistical reporting are complete.

## References

[1] P. Lewis et al., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,” NeurIPS, 2020. https://arxiv.org/abs/2005.11401
[2] A. Radford et al., “Learning Transferable Visual Models From Natural Language Supervision,” ICML, 2021. https://arxiv.org/abs/2103.00020
[3] J. Li et al., “BLIP: Bootstrapping Language-Image Pre-training for Unified Vision-Language Understanding and Generation,” ICML, 2022. https://arxiv.org/abs/2201.12086
[4] A. Radford et al., “Robust Speech Recognition via Large-Scale Weak Supervision,” 2022. https://arxiv.org/abs/2212.04356
[5] R. Friel, M. Belyi, and A. Sanyal, “RAGBench: Explainable Benchmark for Retrieval-Augmented Generation Systems,” 2024. https://arxiv.org/abs/2407.11005
[6] X. Yang et al., “CRAG -- Comprehensive RAG Benchmark,” NeurIPS, 2024. https://proceedings.neurips.cc/paper_files/paper/2024/hash/1435d2d0fca85a84d83ddcb754f58c29-Abstract-Datasets_and_Benchmarks_Track.html
[7] K. Dong et al., “Benchmarking Retrieval-Augmented Multimodal Generation for Document Question Answering,” 2025. https://arxiv.org/abs/2505.16470
[8] X. Ma et al., “VISA: Retrieval Augmented Generation with Visual Source Attribution,” ACL, 2025. https://aclanthology.org/2025.acl-long.1456/
