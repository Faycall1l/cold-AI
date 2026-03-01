from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemoryCandidate:
    owner_key: str
    channel: str
    purpose: str
    specialty: str
    pattern_text: str
    quality_score: float
    source_event: str


def build_memory_seed(context: dict[str, Any], subject: str, body: str, score: float, source_event: str) -> MemoryCandidate:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    opener = lines[0] if lines else body.strip()
    opener = opener[:180]

    cta = ""
    for line in lines[-4:]:
        lower = line.lower()
        if "?" in line or "would you" in lower or "open to" in lower:
            cta = line[:180]
            break

    pattern_parts = [
        f"subject_style={subject[:100]}",
        f"opener={opener}",
    ]
    if cta:
        pattern_parts.append(f"cta={cta}")

    return MemoryCandidate(
        owner_key=str(context.get("owner_key") or "global"),
        channel=str(context.get("channel") or "email").strip().lower() or "email",
        purpose=str(context.get("purpose") or "").strip(),
        specialty=str(context.get("specialty") or "").strip(),
        pattern_text=" | ".join(pattern_parts)[:600],
        quality_score=max(0.0, min(1.0, float(score))),
        source_event=source_event,
    )


def format_memory_for_prompt(memories: list[dict[str, Any]]) -> list[str]:
    formatted: list[str] = []
    for memory in memories:
        channel = str(memory.get("channel") or "email")
        specialty = str(memory.get("specialty") or "general")
        score = float(memory.get("quality_score") or 0.0)
        text = str(memory.get("pattern_text") or "")
        if not text:
            continue
        formatted.append(f"[{channel} | {specialty} | score={score:.2f}] {text}")
    return formatted
