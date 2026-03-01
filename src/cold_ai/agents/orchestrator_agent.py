from __future__ import annotations

from .copywriter_agent import CopywriterAgent
from .lead_intelligence_agent import LeadIntelligenceAgent
from .reflection_agent import ReflectionAgent
from .research_agent import ResearchAgent
from .rewrite_agent import RewriteAgent
from .routing_agent import RoutingAgent
from .supervisor_agent import SupervisorAgent
from ..config import settings
from ..tools import (
    EmailTool,
    OutreachKnowledgeTool,
    OutreachMemoryTool,
    TelegramTool,
    ToolPolicy,
    ToolRegistry,
    WebSearchTool,
    WhatsAppTool,
)


class OrchestratorAgent:
    def __init__(self, agent_settings: dict | None = None) -> None:
        self.agent_settings = agent_settings or {}
        self.lead_agent = LeadIntelligenceAgent()
        self.research_agent = ResearchAgent(agent_settings=self.agent_settings)
        self.routing_agent = RoutingAgent(agent_settings=self.agent_settings)
        self.copywriter = CopywriterAgent()
        self.rewrite_agent = RewriteAgent(agent_settings=self.agent_settings)
        self.reflection_agent = ReflectionAgent(agent_settings=self.agent_settings)
        self.supervisor_agent = SupervisorAgent(agent_settings=self.agent_settings)
        self.tools = ToolRegistry(
            policy=ToolPolicy(
                profile=settings.tool_profile,
                allow=settings.tools_allow,
                deny=settings.tools_deny,
            )
        )
        self.tools.register(EmailTool())
        self.tools.register(WhatsAppTool())
        self.tools.register(TelegramTool())
        self.tools.register(WebSearchTool())
        self.tools.register(OutreachKnowledgeTool())
        self.tools.register(OutreachMemoryTool())

    def prepare_lead(self, lead: dict) -> dict:
        return self.lead_agent.enrich(lead)

    def create_draft(self, subject_template: str, body_template: str, context: dict) -> tuple[str, str]:
        routing_context = self.routing_agent.route(context)
        merged_context = {**context, **routing_context}
        return self.copywriter.draft(subject_template, body_template, merged_context)

    def research(self, lead: dict) -> dict:
        return self.research_agent.research(lead)

    def rewrite(self, subject: str, body: str, context: dict) -> tuple[str, str, str]:
        return self.rewrite_agent.maybe_rewrite(subject, body, context)

    def supervise(self, subject: str, body: str, context: dict) -> dict:
        return self.supervisor_agent.review(subject, body, context)

    def reflect(self, subject: str, body: str, context: dict) -> tuple[str, str, dict]:
        return self.reflection_agent.critique_and_refine(subject, body, context)

    def available_tools(self) -> list[str]:
        return self.tools.available()

    def tool_policy(self) -> dict:
        policy = self.tools.get_policy()
        return {
            "profile": policy.profile,
            "allow": list(policy.allow),
            "deny": list(policy.deny),
            "also_allow": list(policy.also_allow),
        }

    def run_tool(self, tool_name: str, payload: dict) -> dict:
        result = self.tools.run(tool_name, payload)
        return {
            "ok": result.ok,
            "tool": result.tool,
            "data": result.data,
            "error": result.error,
        }
