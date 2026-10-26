# Release audit — 26 October 2026

## Decision

**The hash/extractive preview is suitable for a controlled demonstration after the main-branch CI passes. The full stack is not cleared for a public, persistent enterprise deployment.** The hosted UI overview is a separate sample-data preview and does not exercise this repository's API.

This review covers the repository's API, frontend, migrations, tests, dependency lockfile, demo container, and deployment configuration. It cannot prove the absence of every defect or establish model accuracy. No production cloud instance, PostgreSQL/Redis/Celery/Qdrant-server stack, or paid/local LLM provider was exercised in this audit.

## Corrected and checked

| Area | Change | Verification |
| --- | --- | --- |
| Index completeness | Oversized preserved segments are split without losing the tail; table parts repeat headers and carry part metadata. Removed the silent 20,000-character indexing cut. | Large JSON/table regression tests and full backend suite. |
| Spreadsheet completeness | More than 100,000 rows in a CSV/XLSX sheet now fail indexing explicitly instead of silently dropping rows. | CSV boundary regression test. |
| Offline retrieval | Hash-vector demo returns no evidence when no query term occurs in the selected passages. | Search/chat abstention regression test. Semantic-model relevance still needs labeled evaluation. |
| Authentication | Refresh-token redemption is one conditional database update, preventing two successful redemptions of the same token. | Existing rotation and replay endpoint test; concurrent load testing remains required. |
| Search filters | Tags match whole tags instead of substrings. | Search regression test. |
| Frontend supply chain | Updated vulnerable `follow-redirects` transitive dependency in the lockfile. | `npm ci`, build, and production dependency audit with zero reported advisories. |
| Deployment checks | CI now audits production frontend dependencies and exercises register → upload → indexing → search → cited chat inside the preview container. | Must pass on the main-branch workflow after commit. |

Local verification: 23 backend tests plus 3 subtests passed, Python compiled, SQLite migration upgrade/downgrade/upgrade passed, and the React production build passed. Docker was unavailable in the audit environment, so the new container workflow is the release gate for the preview. Warnings remain from the test client's evolving upstream API and Qdrant's local payload-index behavior; neither warning indicates a failed test.

## Gates before public deployment

1. **Credentials and browser security:** move refresh credentials out of JavaScript-readable session storage, add secure cookie/CSRF handling, HTTPS, CSP, and a documented secret-rotation process.
2. **Untrusted input isolation:** sandbox document/media decoders, scan uploads, bound parser CPU, memory, page count, image dimensions, and archive expansion, and enforce per-user storage and model-cost quotas.
3. **Durability:** exercise PostgreSQL, Redis/Celery, and Qdrant server together with persistent storage; rehearse backup/restore, queue failure, worker crash, retry, and index reconciliation. The Compose file is a starting point, not a public ingress configuration.
4. **Quality evidence:** collect a held-out, human-labeled multimodal dataset and report retrieval recall, citation support, false acceptance/refusal, source-location accuracy, and p95 latency. The current citation audit checks structure and exact numbers, not semantic truth.
5. **Operations:** pin image/model/dependency versions, monitor queues and provider failures, load-test with realistic files and concurrent users, and complete an external security review before accepting confidential material.

## Research features worth building next

The strongest candidate is a **version-aware cross-modal evidence graph**: break answers into claims, connect each claim to an exact version/page/row/time region, explicitly mark conflicts and uncertain OCR/ASR/chart readings, and withhold unsupported claims. This is a proposed extension, not a completed or proven novel method. Compare against version-aware RAG, visual attribution, and multimodal verification baselines rather than claiming these ingredients are new.

A second experiment is **query-adaptive temporal video retrieval**: search transcript, OCR, keyframes, and audio at coarse-to-fine time scales; return exact timestamps for multi-hop questions. Evaluate temporal IoU, evidence recall, answer support, and latency against fixed-interval retrieval. A third is a **human correction loop** that stores reviewer edits as versioned annotations and measures whether corrections improve held-out results without leaking access after grant revocation.

Related primary work: [VersionRAG](https://arxiv.org/abs/2510.08109), [VideoRAG](https://arxiv.org/abs/2502.01549), [VISA](https://aclanthology.org/2025.acl-long.1456/), and [MuSciClaims](https://aclanthology.org/2025.ijcnlp-long.175/).
