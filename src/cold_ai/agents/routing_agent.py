from __future__ import annotations

from ..services.ai_agent_runtime import resolve_agent_llm_config
from ..services.llm_router import LLMRouter
from ..services.outreach_knowledge_base import build_outreach_knowledge_context


class RoutingAgent:
    def __init__(self, agent_settings: dict | None = None) -> None:
        self.llm = LLMRouter()
        self.runtime = resolve_agent_llm_config(agent_settings)

    def route(self, context: dict) -> dict:
        knowledge = build_outreach_knowledge_context(
            channel=str(context.get("channel") or "email"),
            purpose=str(context.get("purpose") or ""),
            specialty=str(context.get("specialty") or ""),
        )

        fallback = {
            "routing_angle": (
                context.get("personalization_hook")
                or (knowledge.get("purpose_angles") or ["practice growth"])[0]
            ),
            "routing_cta": (knowledge.get("cta_examples") or ["Would you be open to a short 15-minute intro call next week?"])[0],
        }

        result = self.llm.run_json_task(
            system_prompt=self.runtime.prompt_routing,
            payload={
                "lead": {
                    "full_name": context.get("full_name"),
                    "specialty": context.get("specialty"),
                    "city": context.get("city"),
                },
                "campaign": {
                    "channel": context.get("channel") or "email",
                    "purpose": context.get("purpose") or "",
                },
                "knowledge": {
                    "principles": knowledge.get("principles") or [],
                    "followup_plan": knowledge.get("followup_plan") or [],
                    "purpose_angles": knowledge.get("purpose_angles") or [],
                    "specialty_hook": knowledge.get("specialty_hook") or "",
                    "cta_examples": knowledge.get("cta_examples") or [],
                },
                "output_schema": {
                    "routing_angle": "string",
                    "routing_cta": "string",
                },
            },
            runtime_config=self.runtime,
            temperature=0.2,
        )

        if not result:
            return fallback

        return {
            "routing_angle": str(result.get("routing_angle") or fallback["routing_angle"]),
            "routing_cta": str(result.get("routing_cta") or fallback["routing_cta"]),
        }
