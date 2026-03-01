from __future__ import annotations

from ..services.ai_agent_runtime import resolve_agent_llm_config
from ..services.llm_router import LLMRouter
from ..services.outreach_knowledge_base import build_outreach_knowledge_context

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
    def __init__(self, agent_settings: dict | None = None) -> None:
        self.router = LLMRouter()
        self.runtime = resolve_agent_llm_config(agent_settings)

    def maybe_rewrite(self, subject: str, body: str, context: dict) -> tuple[str, str, str]:
        if not self.runtime.enable_llm_rewrite:
            return subject, body, "disabled"

        knowledge = build_outreach_knowledge_context(
            channel=str(context.get("channel") or "email"),
            purpose=str(context.get("purpose") or ""),
            specialty=str(context.get("specialty") or ""),
        )

        payload = {
            "goal": "polish outreach while keeping specific details",
            "tone": "professional, warm, concise, not robotic, not overly salesy",
            "lead_context": {
                "full_name": context.get("full_name"),
                "specialty": context.get("specialty"),
                "city": context.get("city"),
                "research_snippet": context.get("research_snippet"),
            },
            "knowledge": {
                "principles": knowledge.get("principles") or [],
                "followup_plan": knowledge.get("followup_plan") or [],
                "objection_handling": knowledge.get("objection_handling") or [],
                "cta_examples": knowledge.get("cta_examples") or [],
            },
            "draft": {"subject": subject, "body": body},
        }

        rewritten = self.router.rewrite_email(
            payload,
            runtime_config=self.runtime,
            custom_prompt=self.runtime.prompt_rewrite,
        )
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
