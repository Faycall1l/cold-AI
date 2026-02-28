from __future__ import annotations

from .copywriter_agent import CopywriterAgent
from .lead_intelligence_agent import LeadIntelligenceAgent
from .research_agent import ResearchAgent
from .rewrite_agent import RewriteAgent


class OrchestratorAgent:
    def __init__(self) -> None:
        self.lead_agent = LeadIntelligenceAgent()
        self.research_agent = ResearchAgent()
        self.copywriter = CopywriterAgent()
        self.rewrite_agent = RewriteAgent()

    def prepare_lead(self, lead: dict) -> dict:
        return self.lead_agent.enrich(lead)

    def create_draft(self, subject_template: str, body_template: str, context: dict) -> tuple[str, str]:
        return self.copywriter.draft(subject_template, body_template, context)

    def research(self, lead: dict) -> dict:
        return self.research_agent.research(lead)

    def rewrite(self, subject: str, body: str, context: dict) -> tuple[str, str, str]:
        return self.rewrite_agent.maybe_rewrite(subject, body, context)
