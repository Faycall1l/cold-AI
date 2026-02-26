from __future__ import annotations

from ..agents.orchestrator_agent import OrchestratorAgent
from ..repositories import CampaignRepository, DraftRepository, EventRepository, LeadRepository


def generate_drafts(campaign_id: int, limit: int) -> tuple[int, int]:
    campaign = CampaignRepository().get(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {campaign_id} not found")

    leads = LeadRepository().list_for_drafting(limit)
    draft_repository = DraftRepository()
    event_repository = EventRepository()
    orchestrator = OrchestratorAgent()

    created = 0
    ignored = 0

    for lead in leads:
        enriched = orchestrator.prepare_lead(lead)
        context = {
            "first_name": enriched.get("first_name") or "Doctor",
            "full_name": enriched.get("full_name") or "Doctor",
            "email": enriched.get("email"),
            "specialty": enriched.get("specialty") or "your specialty",
            "city": enriched.get("city") or "your city",
            "address": enriched.get("address") or "",
            "personalization_hook": enriched.get("personalization_hook"),
            "resource_link": "https://www.who.int/health-topics/digital-health",
            "sender_name": "Faycal",
            "product_name": "Cold AI",
        }

        subject, body = orchestrator.create_draft(
            campaign["subject_template"],
            campaign["body_template"],
            context,
        )
        inserted = draft_repository.create_or_ignore(campaign_id, enriched["id"], subject, body)
        if inserted:
            created += 1
            event_repository.log("draft_created", {"campaign_id": campaign_id}, draft_id=None)
        else:
            ignored += 1

    return created, ignored
