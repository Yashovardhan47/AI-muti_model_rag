# Atlas: evidence integrity research and product roadmap

## The research question

Can an enterprise multimodal assistant reduce **unsupported claims and stale citations** while preserving useful answers across text, tables, images, audio, video, and logs? A broad list of supported formats is an engineering feature, not by itself a novel research contribution. Atlas should test a specific system hypothesis: an evidence contract that binds each answer claim to an exact source version and location, checks the draft before delivery, and abstains when evidence is inadequate.

The current implementation is an initial version of that contract. Chunks carry modality and page/slide/row/time locations. Answer citations now carry the uploaded file's SHA-256; history marks a citation unavailable if its file was removed, the stored path disappeared, or its database digest no longer matches. Deleting a file also redacts assistant answers that cited it and clears that excerpt from stored citations. Generated claims require valid citation IDs and exact numerical values present in their cited excerpts. A failing draft is withheld, and chat shows source passages with an audit warning. Provider tokens are buffered until this check finishes. **The check is structural and cannot establish entailment, detect all contradictions, or certify answer correctness.** History does not rehash stored bytes on every read or track external document revisions.

## Real-world workflow

An operations analyst uploads an inspection PDF, a maintenance CSV, an incident image, and a meeting recording into their private workspace. They ask which equipment is mentioned in both the inspection and meeting, what measurements were recorded, and who owns a follow-up. Atlas retrieves located excerpts, produces a cited response, and exposes the audit. The analyst opens the source files at the listed page, row, or timestamp and checks the decision. If a file is deleted later, history marks its old citation as unavailable instead of presenting it as live evidence.

## What to build next

| Priority | Feature | User benefit | Research measurement |
| --- | --- | --- | --- |
| 1 | Gold-labeled evaluation corpus with answerable and unanswerable cross-format questions | Makes quality visible instead of relying on a polished demo | Recall@k, MRR, human fact support, abstention, p95 latency |
| 2 | Region-accurate provenance: page bounding boxes, spreadsheet cell ranges, audio/video playback at timestamp | Opens the **specific evidence**, not merely the source file | Locator precision and human verification time |
| 3 | Versioned source families, change detection, reindex reconciliation, and ACL-aware connectors | Keeps answers current as enterprise files and permissions change | Stale-citation detection, revocation latency, index consistency |
| 4 | Contradiction-aware multi-hop evidence graph with explicit "sources disagree" state | Makes comparisons and temporal changes reviewable | Conflict detection precision/recall and cross-source fact support |
| 5 | OCR/ASR/chart uncertainty propagated into retrieval and answer abstention | Avoids treating a guessed chart value like a typed table value | Calibration and answer quality by modality and scan quality |
| 6 | Human correction queue with verified annotations and retraining/evaluation loop | Helps teams repair bad extraction and citations | Error-resolution time and held-out quality after correction |
| 7 | Hardened deployment: file sandbox, malware scanning, quotas, retries, distributed reconciliation, encrypted storage, backups, SSO and source ACLs | Supports repeated operational use | Isolation, failure recovery, load, privacy canaries |

The practical research contribution to target is **version-aware cross-modal evidence integrity**: an evidence graph joining atomic claims to source revisions and exact regions/timestamps, with a conservative abstention policy. Claim it as a *proposal* until the components and controlled evaluation exist. It is distinct from simply adding more LLMs, a chatbot wrapper, or unsupported "confidence percentages."

## Evaluation design

Use consented, de-identified enterprise-like material across the supported modalities. Label evidence locations, atomic answer facts, source revisions, disagreement cases, and unanswerable questions with at least two annotators. Keep a held-out document-family split. Compare lexical, dense, hybrid, hybrid plus reranker, and the version-aware audit layer on the same corpus. Report retrieval recall and MRR, human-judged citation support and conflict detection, false refusal and false acceptance rates, stale-citation detection, median/p95 latency, index cost, and per-modality breakdowns. Include OCR/ASR corruption and source deletion/update stress cases. A syntactically valid citation is never counted as a supported fact without checking its content.

Run the included retrieval harness with a JSONL manifest whose rows contain an actual uploaded file ID and location. For example, a row has keys question, evidence (a list of file_id and location pairs), answerable, and modality. Use the real ID from your isolated benchmark account. The script makes no accuracy claims until run against labeled data. See [TESTING.md](TESTING.md) for commands and interpretation.

## Related work and the novelty boundary

- RAGBench studies explainable RAG evaluation; a traceable citation alone is not factual support. https://arxiv.org/abs/2407.11005
- CRAG measures challenging factual retrieval and answering; its benchmark motivates explicit unanswerable and dynamic-source cases. https://proceedings.neurips.cc/paper_files/paper/2024/hash/1435d2d0fca85a84d83ddcb754f58c29-Abstract-Datasets_and_Benchmarks_Track.html
- MMDocRAG evaluates cross-page, cross-modal document evidence. Atlas must compare against this line of work before claiming a new cross-modal method. https://arxiv.org/abs/2505.16470
- VISA already studies exact visual source attribution. A future Atlas region highlighter should cite and compare against it. https://aclanthology.org/2025.acl-long.1456/

No paper acceptance, patentability, or measured improvement follows from this roadmap alone.
