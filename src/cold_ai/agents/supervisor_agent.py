from __future__ import annotations

from ..services.ai_agent_runtime import resolve_agent_llm_config
from ..services.llm_router import LLMRouter
from ..services.outreach_knowledge_base import build_outreach_knowledge_context


class SupervisorAgent:
    def __init__(self, agent_settings: dict | None = None) -> None:
        self.llm = LLMRouter()
        self.runtime = resolve_agent_llm_config(agent_settings)

    def review(self, subject: str, body: str, context: dict) -> dict:
        knowledge = build_outreach_knowledge_context(
            channel=str(context.get("channel") or "email"),
            purpose=str(context.get("purpose") or ""),
            specialty=str(context.get("specialty") or ""),
        )

        fallback_score = 0.6 if len(body) > 120 and len(subject) > 8 else 0.3

        result = self.llm.run_json_task(
            system_prompt=self.runtime.prompt_supervisor,
            payload={
                "lead": {
                    "full_name": context.get("full_name"),
                    "specialty": context.get("specialty"),
                    "city": context.get("city"),
                },
                "draft": {"subject": subject, "body": body},
                "knowledge": {
                    "principles": knowledge.get("principles") or [],
                    "objection_handling": knowledge.get("objection_handling") or [],
                    "followup_plan": knowledge.get("followup_plan") or [],
                },
                "output_schema": {
                    "status": "approved|needs_revision",
                    "score": "float_0_to_1",
                    "notes": "string",
                },
            },
            runtime_config=self.runtime,
            temperature=0.1,
        )

        if not result:
            return {
                "status": "approved" if fallback_score >= 0.5 else "needs_revision",
                "score": fallback_score,
                "notes": "heuristic fallback",
            }

        score = float(result.get("score") or fallback_score)
        status = str(result.get("status") or ("approved" if score >= 0.5 else "needs_revision"))
        notes = str(result.get("notes") or "")
        return {"status": status, "score": max(0.0, min(1.0, score)), "notes": notes}
