from __future__ import annotations

from ..services.ai_agent_runtime import resolve_agent_llm_config
from ..services.llm_router import LLMRouter
from ..services.outreach_knowledge_base import build_outreach_knowledge_context


class ReflectionAgent:
    def __init__(self, agent_settings: dict | None = None) -> None:
        self.router = LLMRouter()
        self.runtime = resolve_agent_llm_config(agent_settings)

    def critique_and_refine(self, subject: str, body: str, context: dict) -> tuple[str, str, dict]:
        knowledge = build_outreach_knowledge_context(
            channel=str(context.get("channel") or "email"),
            purpose=str(context.get("purpose") or ""),
            specialty=str(context.get("specialty") or ""),
        )
        memory_patterns = context.get("memory_patterns") or []

        payload = {
            "goal": "Self-critique and refine outreach draft before approval",
            "draft": {"subject": subject, "body": body},
            "constraints": {
                "tone": "human, specific, respectful, concise",
                "avoid": ["hype", "spam phrases", "generic claims"],
            },
            "knowledge": {
                "principles": knowledge.get("principles") or [],
                "cta_examples": knowledge.get("cta_examples") or [],
                "followup_plan": knowledge.get("followup_plan") or [],
            },
            "memory_patterns": memory_patterns,
            "output_schema": {
                "subject": "string",
                "body": "string",
                "critique": "string",
                "confidence": "float_0_to_1",
            },
        }

        result = self.router.run_json_task(
            system_prompt=(
                "You are a reflection agent. Critique and improve this draft using provided knowledge and memory patterns. "
                "Keep facts unchanged. Return strict JSON."
            ),
            payload=payload,
            runtime_config=self.runtime,
            temperature=0.2,
        )

        if not result:
            return self._heuristic_refine(subject, body, knowledge)

        new_subject = str(result.get("subject") or subject).strip()
        new_body = str(result.get("body") or body).strip()
        critique = str(result.get("critique") or "llm_reflection").strip()
        confidence = float(result.get("confidence") or 0.55)

        if confidence < 0.45 or len(new_body) < 80:
            return self._heuristic_refine(subject, body, knowledge)

        return new_subject, new_body, {
            "mode": "llm",
            "critique": critique,
            "confidence": max(0.0, min(1.0, confidence)),
        }

    def _heuristic_refine(self, subject: str, body: str, knowledge: dict) -> tuple[str, str, dict]:
        revised_subject = " ".join(subject.split())[:120]
        revised_body = "\n".join(line.rstrip() for line in body.splitlines())
        revised_body = revised_body.strip()

        critique_points: list[str] = []

        if len(revised_subject) < 8:
            revised_subject = "Quick question for your practice"
            critique_points.append("Subject too short; replaced with clear non-hype subject.")

        if len(revised_body) > 420:
            revised_body = revised_body[:420].rstrip() + "..."
            critique_points.append("Body shortened for first-touch readability.")

        lowered = revised_body.lower()
        if "would you be open to" not in lowered and "?" not in revised_body:
            cta_examples = knowledge.get("cta_examples") or []
            cta = cta_examples[0] if cta_examples else "Would you be open to a short 15-minute intro next week?"
            revised_body = f"{revised_body}\n\n{cta}".strip()
            critique_points.append("Added clear low-friction CTA.")

        if not critique_points:
            critique_points.append("Heuristic reflection found no critical issues.")

        return revised_subject, revised_body, {
            "mode": "heuristic",
            "critique": " ".join(critique_points),
            "confidence": 0.62,
        }
