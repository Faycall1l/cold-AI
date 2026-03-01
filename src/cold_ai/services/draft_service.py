from __future__ import annotations

from ..agents.orchestrator_agent import OrchestratorAgent
from ..repositories import (
    AgentSettingsRepository,
    CampaignRepository,
    DraftRepository,
    EventRepository,
    LeadRepository,
    OutreachMemoryRepository,
)
from .template_router import SpecialtyTemplateRouter
from .outreach_knowledge_base import build_outreach_knowledge_context
from .outreach_memory import build_memory_seed, format_memory_for_prompt


def generate_drafts(campaign_id: int, limit: int, owner_key: str | None = None) -> tuple[int, int]:
    campaign = CampaignRepository().get(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {campaign_id} not found")

    channel = campaign.get("channel") or "email"
    leads = LeadRepository().list_for_drafting(limit, channel=channel)
    draft_repository = DraftRepository()
    event_repository = EventRepository()
    memory_repository = OutreachMemoryRepository()
    agent_settings = AgentSettingsRepository().get_by_owner(owner_key) if owner_key else None
    orchestrator = OrchestratorAgent(agent_settings=agent_settings)
    template_router = SpecialtyTemplateRouter()

    created = 0
    ignored = 0

    for lead in leads:
        enriched = orchestrator.prepare_lead(lead)
        research = orchestrator.research(enriched)

        selected_subject_template, selected_body_template, template_source = template_router.select(
            enriched.get("specialty") or "",
            campaign["subject_template"],
            campaign["body_template"],
        )

        context = {
            "first_name": enriched.get("first_name") or "Doctor",
            "full_name": enriched.get("full_name") or "Doctor",
            "email": enriched.get("email"),
            "phone": enriched.get("phone"),
            "specialty": enriched.get("specialty") or "your specialty",
            "city": enriched.get("city") or "your city",
            "address": enriched.get("address") or "",
            "channel": campaign.get("channel") or "email",
            "purpose": campaign.get("purpose") or "",
            "personalization_hook": enriched.get("personalization_hook"),
            "resource_link": research.get("resource_link"),
            "research_snippet": research.get("research_snippet") or "",
            "research_source_link": research.get("research_source_link") or "",
            "sender_name": "Faycal",
            "product_name": "Cold AI",
            "owner_key": owner_key or "global",
        }

        memories = memory_repository.list_for_context(
            owner_key=str(owner_key or "global"),
            channel=context["channel"],
            purpose=context["purpose"] or None,
            specialty=context["specialty"] or None,
            limit=5,
        )
        context["memory_patterns"] = format_memory_for_prompt(memories)

        kb_context = build_outreach_knowledge_context(
            channel=context["channel"],
            purpose=context["purpose"],
            specialty=context["specialty"],
        )
        context.update(
            {
                "knowledge_principles": kb_context.get("principles") or [],
                "knowledge_followup_plan": kb_context.get("followup_plan") or [],
                "knowledge_purpose_angles": kb_context.get("purpose_angles") or [],
                "knowledge_specialty_hook": kb_context.get("specialty_hook") or "",
                "knowledge_objection_handling": kb_context.get("objection_handling") or [],
                "knowledge_cta_examples": kb_context.get("cta_examples") or [],
            }
        )

        subject, body = orchestrator.create_draft(
            selected_subject_template,
            selected_body_template,
            context,
        )

        subject, body, rewrite_status = orchestrator.rewrite(subject, body, context)
        subject, body, reflection = orchestrator.reflect(subject, body, context)
        supervision = orchestrator.supervise(subject, body, context)

        inserted = draft_repository.create_or_ignore(campaign_id, enriched["id"], subject, body)
        if inserted:
            created += 1
            event_repository.log(
                "draft_created",
                {
                    "campaign_id": campaign_id,
                    "template_source": template_source,
                    "rewrite_status": rewrite_status,
                    "reflection_mode": reflection.get("mode"),
                    "reflection_confidence": reflection.get("confidence"),
                    "supervisor_status": supervision.get("status"),
                    "supervisor_score": supervision.get("score"),
                    "has_research_snippet": bool(context["research_snippet"]),
                },
                draft_id=None,
            )

            memory_ids = [int(item["id"]) for item in memories if item.get("id") is not None]
            memory_repository.mark_used(memory_ids)

            if float(supervision.get("score") or 0.0) >= 0.78:
                candidate = build_memory_seed(
                    context=context,
                    subject=subject,
                    body=body,
                    score=float(supervision.get("score") or 0.0),
                    source_event="draft_supervised",
                )
                memory_repository.add_memory(
                    owner_key=candidate.owner_key,
                    channel=candidate.channel,
                    purpose=candidate.purpose,
                    specialty=candidate.specialty,
                    pattern_text=candidate.pattern_text,
                    quality_score=candidate.quality_score,
                    source_event=candidate.source_event,
                )
        else:
            ignored += 1

    return created, ignored
