from __future__ import annotations

from datetime import datetime, timezone

from ..repositories import DraftRepository, EventRepository, OutreachMemoryRepository
from .email_provider import ConsoleEmailProvider, SMTPEmailProvider
from .outreach_memory import build_memory_seed
from .whatsapp_provider import ConsoleWhatsAppProvider, UnconfiguredWhatsAppProvider


def send_due(dry_run: bool = False, campaign_id: int | None = None) -> tuple[int, int]:
    now_iso = datetime.now(timezone.utc).isoformat()
    drafts = DraftRepository().list_due(now_iso, campaign_id=campaign_id)
    repository = DraftRepository()
    event_repository = EventRepository()
    memory_repository = OutreachMemoryRepository()
    email_provider = ConsoleEmailProvider() if dry_run else SMTPEmailProvider()
    whatsapp_provider = ConsoleWhatsAppProvider() if dry_run else UnconfiguredWhatsAppProvider()

    sent = 0
    failed = 0

    for draft in drafts:
        try:
            channel = (draft.get("channel") or "email").lower()
            if channel == "whatsapp":
                to_phone = (draft.get("phone") or "").strip()
                if not to_phone:
                    raise ValueError("Missing lead phone number for WhatsApp draft")
                whatsapp_provider.send(to_phone, draft["body"])
                event_repository.log("whatsapp_sent", {"to": to_phone}, draft_id=draft["id"])
            else:
                to_email = (draft.get("email") or "").strip()
                if not to_email:
                    raise ValueError("Missing lead email for email draft")
                email_provider.send(to_email, draft["subject"], draft["body"])
                event_repository.log("email_sent", {"to": to_email}, draft_id=draft["id"])

            repository.mark_sent(draft["id"])

            memory_candidate = build_memory_seed(
                context={
                    "owner_key": "global",
                    "channel": draft.get("channel") or "email",
                    "purpose": draft.get("purpose") or "",
                    "specialty": draft.get("specialty") or "",
                },
                subject=str(draft.get("subject") or ""),
                body=str(draft.get("body") or ""),
                score=0.82,
                source_event="sent_success",
            )
            memory_repository.add_memory(
                owner_key=memory_candidate.owner_key,
                channel=memory_candidate.channel,
                purpose=memory_candidate.purpose,
                specialty=memory_candidate.specialty,
                pattern_text=memory_candidate.pattern_text,
                quality_score=memory_candidate.quality_score,
                source_event=memory_candidate.source_event,
            )

            sent += 1
        except Exception as exc:
            repository.mark_failed(draft["id"], str(exc))
            event_repository.log("send_failed", {"error": str(exc), "channel": draft.get("channel") or "email"}, draft_id=draft["id"])
            failed += 1

    return sent, failed
