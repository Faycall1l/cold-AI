from __future__ import annotations

from datetime import datetime, timezone

from ..repositories import DraftRepository, EventRepository
from .email_provider import ConsoleEmailProvider, SMTPEmailProvider


def send_due(dry_run: bool = False) -> tuple[int, int]:
    now_iso = datetime.now(timezone.utc).isoformat()
    drafts = DraftRepository().list_due(now_iso)
    repository = DraftRepository()
    event_repository = EventRepository()
    provider = ConsoleEmailProvider() if dry_run else SMTPEmailProvider()

    sent = 0
    failed = 0

    for draft in drafts:
        try:
            provider.send(draft["email"], draft["subject"], draft["body"])
            repository.mark_sent(draft["id"])
            event_repository.log("email_sent", {"to": draft["email"]}, draft_id=draft["id"])
            sent += 1
        except Exception as exc:
            repository.mark_failed(draft["id"], str(exc))
            event_repository.log("email_failed", {"error": str(exc)}, draft_id=draft["id"])
            failed += 1

    return sent, failed
