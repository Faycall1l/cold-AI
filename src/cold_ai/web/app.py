from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dateutil import parser
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..repositories import CampaignRepository, DraftRepository
from ..services.send_service import send_due

app = FastAPI(title="cold-AI Review UI", version="0.1.1")

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"

app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")


def _to_utc_iso(value: str) -> str:
    if not value.strip():
        return datetime.now(timezone.utc).isoformat()
    dt = parser.isoparse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class ApproveDraftPayload(BaseModel):
    scheduled_at: str = ""


class SendDuePayload(BaseModel):
    dry_run: bool = True


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/campaigns")
def list_campaigns() -> dict:
    campaigns = CampaignRepository().list_all()
    return {"campaigns": campaigns}


@app.get("/api/campaigns/{campaign_id}")
def campaign_details(campaign_id: int) -> dict:
    campaign = CampaignRepository().get(campaign_id)
    if not campaign:
        return {"campaign": None, "drafts": []}

    drafts = DraftRepository().list_for_campaign(campaign_id)
    return {"campaign": campaign, "drafts": drafts}


@app.post("/api/drafts/{draft_id}/approve")
def approve_draft(draft_id: int, payload: ApproveDraftPayload) -> dict:
    DraftRepository().approve_and_schedule(draft_id, _to_utc_iso(payload.scheduled_at))
    return {"ok": True, "draft_id": draft_id}


@app.post("/api/drafts/{draft_id}/reject")
def reject_draft(draft_id: int) -> dict:
    DraftRepository().mark_rejected(draft_id)
    return {"ok": True, "draft_id": draft_id}


@app.post("/api/campaigns/{campaign_id}/send-due")
def send_due_campaign(campaign_id: int, payload: SendDuePayload) -> dict:
    sent, failed = send_due(dry_run=payload.dry_run)
    return {
        "ok": True,
        "campaign_id": campaign_id,
        "dry_run": payload.dry_run,
        "sent": sent,
        "failed": failed,
    }
