"""Run a labeled, owner-scoped retrieval study against a running Atlas API.

Dataset format: JSONL with question, evidence [{file_id, location}], modality,
and answerable. Set ATLAS_BENCHMARK_TOKEN to a test account's access token.
The default measures retrieval only and does not call a paid answer provider.
"""
import argparse
import json
import os
import statistics
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def score_case(gold: list[dict], hits: list[dict], answerable: bool, audit: dict | None = None) -> dict:
    expected = {(item["file_id"], item["location"]) for item in gold}
    found = [(hit["file_id"], hit["location"]) for hit in hits]
    positions = [i + 1 for i, source in enumerate(found) if source in expected]
    result = {"evidence_recall": len(expected.intersection(found)) / len(expected) if expected else None,
              "reciprocal_rank": 1 / min(positions) if positions else (0.0 if expected else None)}
    if audit is not None:
        result["abstention_correct"] = bool(audit.get("abstained", False)) == (not answerable)
        result["audit_status"] = audit.get("status", "missing")
    return result


def summarize(records: list[dict]) -> dict:
    def mean(key: str):
        values = [float(record[key]) for record in records if record.get(key) is not None]
        return round(statistics.mean(values), 4) if values else None
    latencies = sorted(record["latency_ms"] for record in records)
    p95 = latencies[max(0, (95 * len(latencies) + 99) // 100 - 1)] if latencies else None
    return {"cases": len(records), "evidence_recall_at_k": mean("evidence_recall"),
            "mean_reciprocal_rank": mean("reciprocal_rank"),
            "abstention_accuracy": mean("abstention_correct"),
            "median_latency_ms": round(statistics.median(latencies), 1) if latencies else None,
            "p95_latency_ms": round(p95, 1) if p95 is not None else None}


def api_json(base: str, path: str, token: str, payload: dict | None = None) -> dict | list:
    request = Request(base.rstrip("/") + path,
                      data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                      method="POST" if payload is not None else "GET")
    with urlopen(request, timeout=240) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="Labeled JSONL of real uploaded files")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--answers", action="store_true", help="Call the configured answer provider too; may incur cost")
    parser.add_argument("--output", type=Path, help="Write the report as JSON")
    args = parser.parse_args()
    if not 1 <= args.top_k <= 20:
        parser.error("top-k must be between 1 and 20")
    token = os.getenv("ATLAS_BENCHMARK_TOKEN", "")
    if not token:
        parser.error("Set ATLAS_BENCHMARK_TOKEN for a dedicated test account")
    records = []
    for line_number, line in enumerate(args.dataset.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item.get("question"), str) or not isinstance(item.get("evidence"), list) or not isinstance(item.get("answerable"), bool):
            parser.error("Invalid question, evidence or answerable at line " + str(line_number))
        started = time.monotonic()
        hits = api_json(args.api_base, "/search?" + urlencode({"q": item["question"], "top_k": args.top_k}), token)
        audit = None
        if args.answers:
            response = api_json(args.api_base, "/chat/query", token,
                                {"question": item["question"], "top_k": args.top_k})
            audit = response["audit"]
        score = score_case(item["evidence"], hits, item["answerable"], audit)
        records.append({"case": line_number, "modality": item.get("modality", "unspecified"),
                        "language": item.get("language", "unspecified"),
                        "latency_ms": round((time.monotonic() - started) * 1000, 1), **score})
    by_modality = {name: summarize([record for record in records if record["modality"] == name])
                   for name in sorted({record["modality"] for record in records})}
    by_language = {name: summarize([record for record in records if record["language"] == name])
                   for name in sorted({record["language"] for record in records})}
    report = {"dataset": str(args.dataset), "top_k": args.top_k, "answers": args.answers,
              "overall": summarize(records), "by_modality": by_modality, "by_language": by_language,
              "cases": records, "scope": "Retrieval and structural abstention; semantic faithfulness requires human review."}
    output = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
