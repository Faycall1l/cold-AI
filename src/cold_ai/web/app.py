from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from dateutil import parser
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.sessions import SessionMiddleware

from ..config import settings
from ..repositories import (
    AgentSettingsRepository,
    CampaignRepository,
    DraftRepository,
    OutreachMemoryRepository,
    TemplateLibraryRepository,
    UserRepository,
)
from ..services.draft_service import generate_drafts
from ..services.ai_agent_runtime import list_provider_options, resolve_agent_llm_config
from ..services.guardrails import (
    GuardrailError,
    validate_campaign_channel,
    validate_campaign_inputs,
    validate_draft_content,
    validate_agent_settings_payload,
    validate_template_library_entry,
)
from ..services.llm_router import LLMRouter
from ..services.send_service import send_due

app = FastAPI(title="cold-AI Review UI", version="0.1.1")

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"

app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    max_age=settings.session_max_age_seconds,
)

oauth = OAuth()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

if settings.oauth_google_client_id and settings.oauth_google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.oauth_google_client_id,
        client_secret=settings.oauth_google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


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


class CreateCampaignPayload(BaseModel):
    name: str
    purpose: str = ""
    channel: str = "email"
    subject_template: str
    body_template: str


class GenerateDraftsPayload(BaseModel):
    limit: int = 100


class UpdateDraftPayload(BaseModel):
    subject: str
    body: str


class EmailSignupPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)


class EmailSigninPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordPayload(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TemplateLibraryPayload(BaseModel):
    title: str
    category: str
    content: str


class AgentSettingsPayload(BaseModel):
    llm_provider: str = "openai"
    llm_base_url: str
    llm_api_key: str = ""
    llm_models: list[str] = []
    enable_web_research: bool = False
    enable_llm_rewrite: bool = False
    prompt_search: str
    prompt_routing: str
    prompt_supervisor: str
    prompt_rewrite: str


class AgentSettingsTestPayload(BaseModel):
    llm_provider: str = "openai"
    llm_base_url: str | None = None
    llm_api_key: str = ""
    llm_model: str | None = None


class OutreachMemoryClearPayload(BaseModel):
    channel: str | None = None


def _owner_key_from_session_user(session_user: dict) -> str:
    provider = str(session_user.get("provider") or "unknown")
    sub = str(session_user.get("sub") or "anonymous")
    return f"{provider}:{sub}"


DEFAULT_PROMPTS = {
    "prompt_search": (
        "You are the Search Agent for medical outreach. Produce one high-signal search query and extract only useful,"
        " factual context about specialty/city fit. Ignore irrelevant noise and return concise evidence."
    ),
    "prompt_routing": (
        "You are the Routing Agent. Decide communication strategy and messaging angle for this lead."
        " Prioritize credibility, local context, and channel fit without hype."
    ),
    "prompt_supervisor": (
        "You are the Supervisor Agent. Audit quality and safety of the draft before send."
        " Reject spammy claims, weak personalization, or unclear CTA."
    ),
    "prompt_rewrite": (
        "You are the Rewrite Agent. Rewrite for clarity, warm professional tone, and concrete personalization."
        " Keep it concise and realistic."
    ),
}


def require_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "start.html")


@app.get("/app")
def app_index(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/me")
def me(request: Request) -> dict:
    user = request.session.get("user")
    return {"authenticated": bool(user), "user": user}


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "cold-ai-review-ui"}


@app.get("/auth/providers")
def auth_providers() -> dict:
    return {
        "google": bool(settings.oauth_google_client_id and settings.oauth_google_client_secret),
        "email": True,
    }


@app.get("/api/campaigns")
def list_campaigns(request: Request) -> dict:
    require_user(request)
    campaigns = CampaignRepository().list_all()
    return {"campaigns": campaigns}


@app.post("/api/campaigns")
def create_campaign(payload: CreateCampaignPayload, request: Request) -> dict:
    require_user(request)
    try:
        validated = validate_campaign_inputs(
            payload.name,
            payload.purpose,
            payload.subject_template,
            payload.body_template,
        )
    except GuardrailError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    try:
        validated_channel = validate_campaign_channel(payload.channel)
    except GuardrailError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    campaign_id = CampaignRepository().create(
        validated["name"],
        validated["purpose"] or None,
        validated_channel,
        validated["subject_template"],
        validated["body_template"],
    )
    return {"ok": True, "campaign_id": campaign_id}


@app.get("/api/campaigns/{campaign_id}")
def campaign_details(campaign_id: int, request: Request) -> dict:
    require_user(request)
    campaign = CampaignRepository().get(campaign_id)
    if not campaign:
        return {"campaign": None, "drafts": []}

    drafts = DraftRepository().list_for_campaign(campaign_id)
    return {"campaign": campaign, "drafts": drafts}


@app.post("/api/drafts/{draft_id}/approve")
def approve_draft(draft_id: int, payload: ApproveDraftPayload, request: Request) -> dict:
    require_user(request)
    DraftRepository().approve_and_schedule(draft_id, _to_utc_iso(payload.scheduled_at))
    return {"ok": True, "draft_id": draft_id}


@app.post("/api/drafts/{draft_id}/reject")
def reject_draft(draft_id: int, request: Request) -> dict:
    require_user(request)
    DraftRepository().mark_rejected(draft_id)
    return {"ok": True, "draft_id": draft_id}


@app.patch("/api/drafts/{draft_id}")
def update_draft(draft_id: int, payload: UpdateDraftPayload, request: Request) -> dict:
    require_user(request)
    try:
        validated = validate_draft_content(payload.subject, payload.body)
    except GuardrailError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    DraftRepository().update_content(
        draft_id=draft_id,
        subject=validated["subject"],
        body=validated["body"],
    )
    return {"ok": True, "draft_id": draft_id}


@app.post("/api/campaigns/{campaign_id}/send-due")
def send_due_campaign(campaign_id: int, payload: SendDuePayload, request: Request) -> dict:
    require_user(request)
    sent, failed = send_due(dry_run=payload.dry_run, campaign_id=campaign_id)
    return {
        "ok": True,
        "campaign_id": campaign_id,
        "dry_run": payload.dry_run,
        "sent": sent,
        "failed": failed,
    }


@app.post("/api/campaigns/{campaign_id}/generate-drafts")
def generate_campaign_drafts(campaign_id: int, payload: GenerateDraftsPayload, request: Request) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    created, ignored = generate_drafts(
        campaign_id=campaign_id,
        limit=max(1, payload.limit),
        owner_key=owner_key,
    )
    return {
        "ok": True,
        "campaign_id": campaign_id,
        "created": created,
        "ignored": ignored,
    }


@app.get("/api/agent-settings")
def get_agent_settings(request: Request) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    settings_row = AgentSettingsRepository().get_by_owner(owner_key) or {}
    llm_models = settings_row.get("llm_models") or list(settings.llm_models)
    llm_provider = settings_row.get("llm_provider") or "openai"
    return {
        "llm_provider": llm_provider,
        "llm_base_url": settings_row.get("llm_base_url") or settings.llm_base_url,
        "llm_api_key": "",
        "has_llm_api_key": bool(settings_row.get("llm_api_key") or settings.llm_api_key),
        "llm_models": llm_models,
        "enable_web_research": bool(
            settings_row.get("enable_web_research")
            if settings_row
            else settings.enable_web_research
        ),
        "enable_llm_rewrite": bool(
            settings_row.get("enable_llm_rewrite")
            if settings_row
            else settings.enable_llm_rewrite
        ),
        "prompt_search": settings_row.get("prompt_search") or DEFAULT_PROMPTS["prompt_search"],
        "prompt_routing": settings_row.get("prompt_routing") or DEFAULT_PROMPTS["prompt_routing"],
        "prompt_supervisor": settings_row.get("prompt_supervisor") or DEFAULT_PROMPTS["prompt_supervisor"],
        "prompt_rewrite": settings_row.get("prompt_rewrite") or DEFAULT_PROMPTS["prompt_rewrite"],
        "provider_options": list_provider_options(),
    }


@app.put("/api/agent-settings")
def update_agent_settings(payload: AgentSettingsPayload, request: Request) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    try:
        validated = validate_agent_settings_payload(payload.model_dump())
    except GuardrailError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    AgentSettingsRepository().upsert_for_owner(
        owner_key=owner_key,
        llm_provider=validated["llm_provider"],
        llm_base_url=validated["llm_base_url"],
        llm_api_key=validated["llm_api_key"] or None,
        llm_models=validated["llm_models"],
        enable_web_research=validated["enable_web_research"],
        enable_llm_rewrite=validated["enable_llm_rewrite"],
        prompt_search=validated["prompt_search"],
        prompt_routing=validated["prompt_routing"],
        prompt_supervisor=validated["prompt_supervisor"],
        prompt_rewrite=validated["prompt_rewrite"],
    )
    return {"ok": True}


@app.post("/api/agent-settings/test")
def test_agent_settings(payload: AgentSettingsTestPayload, request: Request) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    existing = AgentSettingsRepository().get_by_owner(owner_key) or {}

    merged = {
        **existing,
        "llm_provider": payload.llm_provider or existing.get("llm_provider") or "openai",
    }
    if payload.llm_base_url and payload.llm_base_url.strip():
        merged["llm_base_url"] = payload.llm_base_url.strip()
    if payload.llm_api_key and payload.llm_api_key.strip():
        merged["llm_api_key"] = payload.llm_api_key.strip()
    if payload.llm_model and payload.llm_model.strip():
        merged["llm_models"] = [payload.llm_model.strip()]

    runtime_config = resolve_agent_llm_config(merged)
    result = LLMRouter().test_connection(runtime_config)
    return result


@app.get("/api/outreach-memory")
def list_outreach_memory(request: Request, limit: int = 20, channel: str | None = None) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    items = OutreachMemoryRepository().list_by_owner(
        owner_key=owner_key,
        limit=max(1, min(limit, 100)),
        channel=channel,
    )
    return {"items": items, "count": len(items)}


@app.delete("/api/outreach-memory")
def clear_outreach_memory(payload: OutreachMemoryClearPayload, request: Request) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    deleted = OutreachMemoryRepository().clear_by_owner(
        owner_key=owner_key,
        channel=payload.channel,
    )
    return {"ok": True, "deleted": deleted}


@app.get("/api/templates/defaults")
def default_templates(request: Request) -> dict:
    require_user(request)
    templates_dir = WEB_DIR.parents[2] / "templates"
    subject = (templates_dir / "subject_default.txt").read_text(encoding="utf-8")
    body = (templates_dir / "body_default.txt").read_text(encoding="utf-8")
    return {"subject_template": subject, "body_template": body}


@app.get("/api/template-library")
def list_template_library(request: Request) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    entries = TemplateLibraryRepository().list_by_owner(owner_key)
    return {"entries": entries}


@app.post("/api/template-library")
def create_template_library_entry(payload: TemplateLibraryPayload, request: Request) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    try:
        validated = validate_template_library_entry(payload.title, payload.category, payload.content)
    except GuardrailError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    entry_id = TemplateLibraryRepository().create(
        owner_key=owner_key,
        title=validated["title"],
        category=validated["category"],
        content=validated["content"],
    )
    return {"ok": True, "entry_id": entry_id}


@app.patch("/api/template-library/{entry_id}")
def update_template_library_entry(entry_id: int, payload: TemplateLibraryPayload, request: Request) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    try:
        validated = validate_template_library_entry(payload.title, payload.category, payload.content)
    except GuardrailError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    updated = TemplateLibraryRepository().update_for_owner(
        entry_id=entry_id,
        owner_key=owner_key,
        title=validated["title"],
        category=validated["category"],
        content=validated["content"],
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Template entry not found")
    return {"ok": True, "entry_id": entry_id}


@app.delete("/api/template-library/{entry_id}")
def delete_template_library_entry(entry_id: int, request: Request) -> dict:
    session_user = require_user(request)
    owner_key = _owner_key_from_session_user(session_user)
    deleted = TemplateLibraryRepository().delete_for_owner(entry_id=entry_id, owner_key=owner_key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template entry not found")
    return {"ok": True, "entry_id": entry_id}


@app.post("/auth/email/signup")
def auth_email_signup(request: Request, payload: EmailSignupPayload) -> dict:
    repo = UserRepository()
    email = payload.email.strip().lower()
    existing = repo.get_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    user_id = repo.create(
        email=email,
        password_hash=pwd_context.hash(payload.password),
        full_name=(payload.full_name or "").strip() or None,
    )
    user = repo.get_by_id(user_id)
    request.session["user"] = {
        "provider": "email",
        "sub": str(user_id),
        "name": user.get("full_name") or user.get("email"),
        "email": user.get("email"),
        "picture": None,
    }
    return {"ok": True, "user": request.session["user"]}


@app.post("/auth/email/signin")
def auth_email_signin(request: Request, payload: EmailSigninPayload) -> dict:
    repo = UserRepository()
    email = payload.email.strip().lower()
    user = repo.get_by_email(email)
    if not user or not pwd_context.verify(payload.password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    request.session["user"] = {
        "provider": "email",
        "sub": str(user.get("id")),
        "name": user.get("full_name") or user.get("email"),
        "email": user.get("email"),
        "picture": None,
    }
    return {"ok": True, "user": request.session["user"]}


@app.post("/auth/email/change-password")
def auth_email_change_password(request: Request, payload: ChangePasswordPayload) -> dict:
    session_user = require_user(request)
    if session_user.get("provider") != "email":
        raise HTTPException(status_code=400, detail="Password change is only available for email accounts")

    user_id = int(session_user.get("sub"))
    repo = UserRepository()
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_hash = user.get("password_hash") or ""
    if not pwd_context.verify(payload.current_password, current_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=422, detail="New password must be different from current password")

    repo.update_password_hash(user_id, pwd_context.hash(payload.new_password))
    return {"ok": True}


@app.get("/auth/login/google")
async def auth_login_google(request: Request):
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    redirect_uri = f"{settings.app_base_url.rstrip('/')}/auth/callback/google"
    return await client.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback/google")
async def auth_callback_google(request: Request):
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    token = await client.authorize_access_token(request)
    user_payload = token.get("userinfo") or await client.parse_id_token(request, token)

    request.session["user"] = {
        "provider": "google",
        "sub": user_payload.get("sub"),
        "name": user_payload.get("name"),
        "email": user_payload.get("email"),
        "picture": user_payload.get("picture"),
    }
    return RedirectResponse(url="/app", status_code=303)


@app.post("/auth/logout")
def auth_logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}
