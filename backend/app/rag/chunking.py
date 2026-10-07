import re
from app.services.extract import Segment


def split(segments: list[Segment], method: str = "document", size: int = 900, overlap: int = 120, embedder=None) -> list[Segment]:
    output = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        if segment.preserve or (method == "document" and len(text) <= size):
            output.append(segment)
            continue
        if method == "semantic" and embedder:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            vectors = embedder.embed(sentences) if sentences else []
            groups, current = [], []
            for i, sentence in enumerate(sentences):
                similarity = sum(a*b for a, b in zip(vectors[i-1], vectors[i])) if i else 1.0
                if current and (similarity < 0.65 or sum(map(len, current)) + len(sentence) > size):
                    groups.append(" ".join(current)); current = []
                current.append(sentence)
            if current: groups.append(" ".join(current))
        elif method in {"recursive", "document"}:
            paragraphs = re.split(r"\n\s*\n", text)
            groups, current = [], ""
            for paragraph in paragraphs:
                if len(current) + len(paragraph) > size and current:
                    groups.append(current); current = ""
                if len(paragraph) > size:
                    groups.extend(paragraph[i:i+size] for i in range(0, len(paragraph), size))
                else:
                    current += ("\n\n" if current else "") + paragraph
            if current: groups.append(current)
        else:
            groups = [text[i:i+size] for i in range(0, len(text), size-overlap)]
        for group in groups:
            if group.strip():
                locator = segment.locator.copy()
                if locator.get("kind") == "pdf" and locator.get("anchor"):
                    locator["anchor"] = " ".join(group.split()[:8])
                output.append(Segment(group.strip(), segment.location, segment.modality, segment.image,
                                      locator=locator, quality=segment.quality.copy()))
    return output
