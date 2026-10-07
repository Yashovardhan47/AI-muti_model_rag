"""Source-located value changes; potential disagreements require human review."""
import csv
import json
from io import StringIO
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Chunk, File


def _facts(chunks: list[Chunk]) -> dict[tuple[str, str], dict]:
    facts = {}
    for chunk in chunks:
        if chunk.location.endswith("summary") or "log analysis" in chunk.location:
            continue
        rows = []
        if chunk.modality == "table":
            if " | " in chunk.text:
                rows = [[value.strip() for value in line.split(" | ")] for line in chunk.text.splitlines()]
            else:
                rows = list(csv.reader(StringIO(chunk.text)))
        elif chunk.modality == "logs" and chunk.location == "JSON":
            try:
                payload = json.loads(chunk.text)
                records = payload if isinstance(payload, list) else payload.get("records", [])
                if isinstance(records, list) and records and isinstance(records[0], dict):
                    columns = list(dict.fromkeys(key for row in records for key in row))
                    rows = [columns] + [[str(row.get(column, "")) for column in columns] for row in records]
            except (ValueError, TypeError, AttributeError):
                continue
        if len(rows) < 2 or len(rows[0]) < 2:
            continue
        header = [str(value).strip().casefold() for value in rows[0]]
        for row in rows[1:]:
            if len(row) != len(header) or not str(row[0]).strip():
                continue
            identifier = str(row[0]).strip().casefold()
            for column, value in zip(header[1:], row[1:]):
                if not column: continue
                facts[(identifier, column)] = {"value": str(value).strip(), "chunk_id": chunk.id,
                                                "location": chunk.location, "locator": json.loads(chunk.locator_json or "{}")}
    return facts


def _lines(chunks: list[Chunk]) -> dict[str, dict]:
    found = {}
    for chunk in chunks:
        if chunk.modality in {"table", "logs"}: continue
        for raw in chunk.text.splitlines():
            text = " ".join(raw.split())
            if len(text) >= 15:
                found[text.casefold()] = {"text": text[:500], "chunk_id": chunk.id,
                                          "location": chunk.location, "locator": json.loads(chunk.locator_json or "{}")}
    return found


def compare_files(db: Session, left: File, right: File) -> dict:
    chunks_left = db.scalars(select(Chunk).where(Chunk.file_id == left.id).order_by(Chunk.ordinal)).all()
    chunks_right = db.scalars(select(Chunk).where(Chunk.file_id == right.id).order_by(Chunk.ordinal)).all()
    old, new = _facts(chunks_left), _facts(chunks_right)
    changes = []
    for key in sorted(old.keys() & new.keys()):
        if old[key]["value"] != new[key]["value"]:
            changes.append({"record": key[0], "field": key[1], "left": old[key], "right": new[key],
                            "interpretation": "potential_value_disagreement"})
    added = [{"record": key[0], "field": key[1], **new[key]} for key in sorted(new.keys() - old.keys())]
    removed = [{"record": key[0], "field": key[1], **old[key]} for key in sorted(old.keys() - new.keys())]
    before_lines, after_lines = _lines(chunks_left), _lines(chunks_right)
    return {"left": {"id": left.id, "name": left.name, "version": left.version},
            "right": {"id": right.id, "name": right.name, "version": right.version},
            "same_family": left.family_id == right.family_id,
            "changes": changes[:100], "added": added[:100], "removed": removed[:100],
            "text_added": [after_lines[key] for key in sorted(after_lines.keys() - before_lines.keys())[:50]],
            "text_removed": [before_lines[key] for key in sorted(before_lines.keys() - after_lines.keys())[:50]],
            "totals": {"changes": len(changes), "added": len(added), "removed": len(removed),
                       "text_added": len(after_lines.keys() - before_lines.keys()),
                       "text_removed": len(before_lines.keys() - after_lines.keys())},
            "note": "Exact parsed table/log values differ; different units, dates, or contexts may explain them. Review both sources."}
