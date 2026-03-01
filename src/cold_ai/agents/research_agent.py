from __future__ import annotations

from ..services.ai_agent_runtime import resolve_agent_llm_config
from ..services.llm_router import LLMRouter
from ..services.outreach_knowledge_base import build_outreach_knowledge_context
from ..tools.web_search_tool import WebSearchTool

SPECIALTY_RESOURCE_MAP = {
    "dentiste": "https://www.who.int/news-room/fact-sheets/detail/oral-health",
    "cardio": "https://www.who.int/health-topics/cardiovascular-diseases",
    "nutrition": "https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
    "diab": "https://www.who.int/health-topics/diabetes",
    "pedi": "https://www.who.int/health-topics/child-health",
}


class ResearchAgent:
    def __init__(self, agent_settings: dict | None = None) -> None:
        self.llm = LLMRouter()
        self.runtime = resolve_agent_llm_config(agent_settings)
        self.web_search_tool = WebSearchTool()

    def research(self, lead: dict) -> dict:
        specialty = (lead.get("specialty") or "").lower()
        default_resource = "https://www.who.int/health-topics/digital-health"
        resource_link = next(
            (
                url
                for keyword, url in SPECIALTY_RESOURCE_MAP.items()
                if keyword in specialty
            ),
            default_resource,
        )

        web_snippet = ""
        source_link = ""
        knowledge = build_outreach_knowledge_context(
            channel=str(lead.get("channel") or "email"),
            purpose=str(lead.get("purpose") or ""),
            specialty=str(lead.get("specialty") or ""),
        )

        if self.runtime.enable_web_research:
            fallback_query = " ".join(
                value
                for value in [
                    lead.get("full_name") or "",
                    lead.get("specialty") or "",
                    lead.get("city") or "",
                    "doctor Algeria",
                ]
                if value
            )
            llm_query = self.llm.run_json_task(
                system_prompt=self.runtime.prompt_search,
                payload={
                    "lead": {
                        "full_name": lead.get("full_name"),
                        "specialty": lead.get("specialty"),
                        "city": lead.get("city"),
                    },
                    "goal": "Generate one concise web search query for outreach personalization",
                    "output_schema": {"query": "string"},
                },
                runtime_config=self.runtime,
                temperature=0.1,
            )
            query = str((llm_query or {}).get("query") or fallback_query).strip()
            result = self.web_search_tool.run({"query": query})
            if result.ok:
                web_snippet = str(result.data.get("snippet") or "")
                source_link = str(result.data.get("link") or "")

        if not web_snippet:
            web_snippet = str(knowledge.get("specialty_hook") or "")

        return {
            "resource_link": resource_link,
            "research_snippet": web_snippet,
            "research_source_link": source_link,
        }
