from __future__ import annotations

from .copywriter_agent import CopywriterAgent
from .lead_intelligence_agent import LeadIntelligenceAgent


class OrchestratorAgent:
    def __init__(self) -> None:
        self.lead_agent = LeadIntelligenceAgent()
        self.copywriter = CopywriterAgent()

    def prepare_lead(self, lead: dict) -> dict:
        return self.lead_agent.enrich(lead)

    def create_draft(self, subject_template: str, body_template: str, context: dict) -> tuple[str, str]:
        return self.copywriter.draft(subject_template, body_template, context)
