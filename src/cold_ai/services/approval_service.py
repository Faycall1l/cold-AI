from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dateutil import parser

from ..config import settings
from ..repositories import DraftRepository
from .csv_io import read_csv_rows, write_csv_rows


def export_approvals(campaign_id: int) -> Path:
    rows = DraftRepository().list_for_campaign(campaign_id)
    output_rows = []
    for row in rows:
        output_rows.append(
            {
                "draft_id": row["id"],
                "lead_email": row["email"],
                "full_name": row.get("full_name") or "",
                "specialty": row.get("specialty") or "",
                "city": row.get("city") or "",
                "subject": row["subject"],
                "body": row["body"],
                "approved": "",
                "scheduled_at": row.get("scheduled_at") or "",
            }
        )

    settings.export_dir.mkdir(parents=True, exist_ok=True)
    output_path = settings.export_dir / f"campaign_{campaign_id}_approvals.csv"
    write_csv_rows(
        output_path,
        output_rows,
        fieldnames=[
            "draft_id",
            "lead_email",
            "full_name",
            "specialty",
            "city",
            "subject",
            "body",
            "approved",
            "scheduled_at",
        ],
    )
    return output_path


def _parse_scheduled_at(value: str) -> str:
    if not value.strip():
        return datetime.now(timezone.utc).isoformat()
    dt = parser.isoparse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def import_approvals(csv_path: Path) -> tuple[int, int]:
    rows = read_csv_rows(csv_path)
    repository = DraftRepository()
    approved = 0
    rejected = 0

    for row in rows:
        draft_id = int(row["draft_id"])
        decision = (row.get("approved") or "").strip().lower()
        if decision in {"yes", "y", "1", "true", "approved"}:
            scheduled_at = _parse_scheduled_at((row.get("scheduled_at") or "").strip())
            repository.approve_and_schedule(draft_id, scheduled_at)
            approved += 1
        elif decision in {"no", "n", "0", "false", "rejected"}:
            repository.mark_rejected(draft_id)
            rejected += 1

    return approved, rejected
