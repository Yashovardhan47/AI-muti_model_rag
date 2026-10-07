"""Upload a synthetic, labeled multilingual smoke corpus into a test account."""
import argparse
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

from sync_folder import api, multipart

FIXTURES = Path(__file__).resolve().parents[1] / "benchmarks" / "fixture"
CASES = [
    ("When did the cooling pump stop?", "incident.txt", "text", "text", "en"),
    ("Who is responsible for replacing the seal?", "incident.txt", "text", "text", "en"),
    ("Why was the incident marked high severity?", "incident.txt", "text", "text", "en"),
    ("What is the estimated repair cost of P-17?", "assets.csv", "sheet CSV rows 1-3", "table", "en"),
    ("Which asset is operational?", "assets.csv", "sheet CSV rows 1-3", "table", "en"),
    ("What pressure was reported at 09:20?", "sensors.json", "JSON", "logs", "en"),
    ("09:25 पर दबाव कितना था?", "sensors.json", "JSON", "logs", "hi"),
    ("सील बदलने की अंतिम तिथि क्या है?", "maintenance_hi.txt", "text", "text", "hi"),
    ("సీల్ మార్చే బాధ్యత ఎవరికి అప్పగించారు?", "maintenance_te.txt", "text", "text", "te"),
    ("What is the capital of Neptune?", None, None, "unanswerable", "en"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("benchmark-smoke.jsonl"))
    args = parser.parse_args()
    token = os.getenv("ATLAS_BENCHMARK_TOKEN", "")
    if not token: parser.error("Set ATLAS_BENCHMARK_TOKEN for a dedicated test account")
    host = urlparse(args.api_base)
    if host.scheme != "https" and not (host.scheme == "http" and host.hostname in {"localhost", "127.0.0.1"}):
        parser.error("Use HTTPS for remote servers")
    ids = {}
    for path in sorted(FIXTURES.iterdir()):
        body, boundary = multipart(path, "", "document", "eng")
        item = api(args.api_base, token, "/files/upload", body, boundary)
        ids[path.name] = item["id"]
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        statuses = {item["id"]: item for item in api(args.api_base, token, "/files/list")}
        if any(statuses[file_id]["status"] == "failed" for file_id in ids.values()):
            raise RuntimeError("Fixture indexing failed: " + str([statuses[file_id] for file_id in ids.values() if statuses[file_id]["status"] == "failed"]))
        if all(statuses[file_id]["status"] == "ready" for file_id in ids.values()): break
        time.sleep(2)
    else: raise TimeoutError("Fixture indexing did not finish within 180 seconds")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for question, name, location, modality, language in CASES:
            output.write(json.dumps({"question": question, "answerable": name is not None,
                                     "evidence": [{"file_id": ids[name], "location": location}] if name else [],
                                     "modality": modality, "language": language}, ensure_ascii=False) + "\n")
    print(f"Wrote {len(CASES)} labeled cases to {args.output}")


if __name__ == "__main__":
    main()
