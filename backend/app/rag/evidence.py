"""Conservative, deterministic checks before an answer leaves the API.

These checks establish citation traceability and exact numeric presence only.
They do not claim that a cited passage entails a sentence.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Protocol


class LocatedHit(Protocol):
    number: int
    file_name: str
    location: str
    excerpt: str


CITATION = re.compile(r"\[(\d+)\]")
NUMBER = re.compile(r"(?<![\w])[-+]?\d[\d,]*(?:\.\d+)?%?(?![\w])")
SENTENCE = re.compile(r"\n+|(?<=[.!?])\s+(?=[A-Z0-9\"'])|(?<=\])\s+(?=[A-Z0-9\"'])")


def _numbers(text: str) -> set[tuple[Decimal, bool]]:
    found: set[tuple[Decimal, bool]] = set()
    for match in NUMBER.finditer(CITATION.sub("", text)):
        raw = match.group().replace(",", "")
        try:
            found.add((Decimal(raw.rstrip("%")), raw.endswith("%")))
        except InvalidOperation:
            continue
    return found


def _claims(answer: str) -> list[str]:
    return [part.strip(" \t-•*\r") for part in SENTENCE.split(answer)
            if part.strip(" \t-•*\r") and not (part.strip().endswith(":") and len(part.split()) < 4)]


def audit_answer(answer: str, hits: list[LocatedHit], *, extractive: bool = False) -> dict:
    if not hits:
        return {"status": "insufficient", "abstained": True, "checks": [],
                "warnings": ["No indexed source passages were retrieved."]}
    if extractive:
        return {"status": "source_excerpts", "abstained": False, "checks": [],
                "warnings": ["These are direct excerpts, not a synthesized or fact-checked answer."]}

    by_number = {hit.number: hit for hit in hits}
    checks = []
    for claim in _claims(answer):
        citations = list(dict.fromkeys(int(x) for x in CITATION.findall(claim)))
        issues = []
        if not citations:
            issues.append("missing_citation")
        if any(number not in by_number for number in citations):
            issues.append("unknown_citation")
        if citations and not issues:
            evidence = " ".join(by_number[number].excerpt for number in citations)
            if not _numbers(claim).issubset(_numbers(evidence)):
                issues.append("number_not_in_cited_excerpt")
        checks.append({"text": claim[:500], "citation_numbers": citations,
                       "status": "blocked" if issues else "citation_checked", "issues": issues})

    if not checks or any(item["issues"] for item in checks):
        reasons = sorted({issue for item in checks for issue in item["issues"]})
        return {"status": "withheld", "abstained": True, "checks": [],
                "warnings": ["Generated answer withheld: " + (", ".join(reasons) if reasons else "no checkable claims") + "."]}
    return {"status": "citation_checked", "abstained": False, "checks": checks,
            "warnings": ["Citations and exact numbers were checked; semantic support still requires source review."]}


def safe_answer(draft: str, hits: list[LocatedHit], *, extractive: bool = False) -> tuple[str, dict]:
    audit = audit_answer(draft, hits, extractive=extractive)
    if audit["status"] != "withheld":
        return draft, audit
    excerpts = "\n\n".join(
        f"[{hit.number}] {hit.file_name} ({hit.location}): {hit.excerpt[:300]}"
        for hit in hits[:3]
    )
    return "I cannot substantiate a generated answer with these citations. Review the source passages:\n\n" + excerpts, audit
