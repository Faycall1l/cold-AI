from __future__ import annotations

from ..config import settings
from ..services.llm_router import LLMRouter

SPAMMY_TERMS = {
    "guaranteed",
    "limited time",
    "act now",
    "buy now",
    "winner",
    "risk-free",
    "100%",
}


class RewriteAgent:
    def __init__(self) -> None:
        self.router = LLMRouter()

    def maybe_rewrite(self, subject: str, body: str, context: dict) -> tuple[str, str, str]:
        if not settings.enable_llm_rewrite:
            return subject, body, "disabled"

        payload = {
            "goal": "polish outreach while keeping specific details",
            "tone": "professional, warm, concise, not robotic, not overly salesy",
            "lead_context": {
                "full_name": context.get("full_name"),
                "specialty": context.get("specialty"),
                "city": context.get("city"),
                "research_snippet": context.get("research_snippet"),
            },
            "draft": {"subject": subject, "body": body},
        }

        rewritten = self.router.rewrite_email(payload)
        if not rewritten:
            return subject, body, "fallback_no_response"

        new_subject = str(rewritten.get("subject") or "").strip()
        new_body = str(rewritten.get("body") or "").strip()
        confidence = float(rewritten.get("confidence") or 0.0)

        if not self._passes_quality_gate(new_subject, new_body, confidence):
            return subject, body, "fallback_quality_gate"

        return new_subject, new_body, "rewritten"

    def _passes_quality_gate(self, subject: str, body: str, confidence: float) -> bool:
        if confidence < 0.55:
            return False
        if len(subject) < 8 or len(body) < 120:
            return False

        combined = f"{subject} {body}".lower()
        if any(term in combined for term in SPAMMY_TERMS):
            return False

        return True
