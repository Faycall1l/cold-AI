from __future__ import annotations

from ..agents.orchestrator_agent import OrchestratorAgent
from ..repositories import CampaignRepository, DraftRepository, EventRepository, LeadRepository
from .template_router import SpecialtyTemplateRouter


def generate_drafts(campaign_id: int, limit: int) -> tuple[int, int]:
    campaign = CampaignRepository().get(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {campaign_id} not found")

    leads = LeadRepository().list_for_drafting(limit)
    draft_repository = DraftRepository()
    event_repository = EventRepository()
    orchestrator = OrchestratorAgent()
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
            "specialty": enriched.get("specialty") or "your specialty",
            "city": enriched.get("city") or "your city",
            "address": enriched.get("address") or "",
            "personalization_hook": enriched.get("personalization_hook"),
            "resource_link": research.get("resource_link"),
            "research_snippet": research.get("research_snippet") or "",
            "research_source_link": research.get("research_source_link") or "",
            "sender_name": "Faycal",
            "product_name": "Cold AI",
        }

        subject, body = orchestrator.create_draft(
            selected_subject_template,
            selected_body_template,
            context,
        )

        subject, body, rewrite_status = orchestrator.rewrite(subject, body, context)

        inserted = draft_repository.create_or_ignore(campaign_id, enriched["id"], subject, body)
        if inserted:
            created += 1
            event_repository.log(
                "draft_created",
                {
                    "campaign_id": campaign_id,
                    "template_source": template_source,
                    "rewrite_status": rewrite_status,
                    "has_research_snippet": bool(context["research_snippet"]),
                },
                draft_id=None,
            )
        else:
            ignored += 1

    return created, ignored
