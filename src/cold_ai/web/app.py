from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dateutil import parser
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from ..repositories import CampaignRepository, DraftRepository
from ..services.send_service import send_due

app = FastAPI(title="cold-AI Review UI", version="0.1.1")

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates" / "web"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _to_utc_iso(value: str) -> str:
    if not value.strip():
        return datetime.now(timezone.utc).isoformat()
    dt = parser.isoparse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


@app.get("/")
def index(request: Request):
    campaigns = CampaignRepository().list_all()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"campaigns": campaigns},
    )


@app.get("/campaigns/{campaign_id}")
def campaign_details(request: Request, campaign_id: int):
    campaign = CampaignRepository().get(campaign_id)
    if not campaign:
        return RedirectResponse(url="/", status_code=303)

    drafts = DraftRepository().list_for_campaign(campaign_id)
    return templates.TemplateResponse(
        request,
        "campaign.html",
        {
            "campaign": campaign,
            "drafts": drafts,
        },
    )


@app.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id: int, campaign_id: int = Form(...), scheduled_at: str = Form("")):
    DraftRepository().approve_and_schedule(draft_id, _to_utc_iso(scheduled_at))
    return RedirectResponse(url=f"/campaigns/{campaign_id}", status_code=303)


@app.post("/drafts/{draft_id}/reject")
def reject_draft(draft_id: int, campaign_id: int = Form(...)):
    DraftRepository().mark_rejected(draft_id)
    return RedirectResponse(url=f"/campaigns/{campaign_id}", status_code=303)


@app.post("/campaigns/{campaign_id}/send-due")
def send_due_campaign(campaign_id: int, dry_run: str = Form("true")):
    send_due(dry_run=dry_run.lower() == "true")
    return RedirectResponse(url=f"/campaigns/{campaign_id}", status_code=303)
