# cold-AI (Phase 1)

Phase 1 MVP of an agentic cold outreach system focused on:

- Importing leads from CSV
- Generating personalized drafts from templates
- Manual review and approval
- Scheduling
- Sending due outreach (email and WhatsApp dry-run)

## Personalization Engine (Phase 1.2)

Draft generation now follows a multi-step agent flow:

1. lead intelligence normalization
2. specialty template routing
3. optional web research snippet lookup
4. deterministic template drafting
5. optional LLM rewrite pass with quality gate
6. reflection self-critique pass (LLM or heuristic fallback)
7. supervisor quality review
8. fallback-safe deterministic behavior if provider fails

### Optional environment flags

```bash
export COLD_AI_ENABLE_WEB_RESEARCH="true"
export COLD_AI_ENABLE_LLM_REWRITE="true"

export COLD_AI_LLM_API_KEY="..."
export COLD_AI_LLM_BASE_URL="https://api.openai.com/v1"
export COLD_AI_LLM_MODELS="gpt-4o-mini,gpt-4.1-mini"
```

If `COLD_AI_ENABLE_LLM_REWRITE=false` or no API key is set, drafts are still generated via deterministic templates.

## Agent Tool Layer (Phase 2.1 Foundation)

The orchestrator now exposes a reusable tool registry pattern inspired by OSS agent systems, with adapters for:

- `email`
- `whatsapp`
- `telegram`
- `web_search`
- `outreach_knowledge` (static offline copywriting + follow-up playbook)
- `outreach_memory` (local long-term memory retrieval)

This is implemented in `src/cold_ai/tools/*` and can be extended with additional channels/providers.

OpenClaw-inspired policy controls are now supported:

- tool profiles: `minimal`, `messaging`, `full`
- per-env allow/deny lists with alias normalization
- loop protection for repeated identical tool calls

### Static Outreach Knowledge Base (Phase 2.2)

Cold-AI now includes a built-in, offline outreach knowledge base that can be used without any external LLM key.

It currently provides:

- channel-specific copywriting rules (`email`, `whatsapp`, `telegram`)
- follow-up cadence suggestions by channel
- purpose-based messaging angles
- specialty personalization hooks
- objection-handling patterns and CTA examples

Integration points:

- exposed as agent tool: `outreach_knowledge`
- injected into draft context keys (`knowledge_*`)
- consumed by `routing`, `rewrite`, `supervisor`, and `research` agent flows for stronger fallback behavior

### Reflection + Long-Term Memory (Phase 2.3)

Cold-AI now includes two additional OpenClaw-inspired agentic capabilities that work even without API keys:

- reflection self-critique loop before final supervisor scoring
- local long-term memory store for high-quality draft/sent patterns

Memory behavior:

- retrieves best matching memory snippets by owner/channel/purpose/specialty during generation
- injects memory patterns into prompt context for routing/rewrite/reflection
- increments usage counters when a memory was referenced
- learns new memory entries from high-supervisor-score drafts and successful sends

Reference docs: `docs/outreach_knowledge_base.md`

Reference playbook: `docs/outreach_knowledge_base.md`

Policy env vars:

```bash
export COLD_AI_TOOL_PROFILE="messaging"
export COLD_AI_TOOLS_ALLOW=""
export COLD_AI_TOOLS_DENY=""

export COLD_AI_TOOL_LOOP_DETECTION_ENABLED="true"
export COLD_AI_TOOL_LOOP_HISTORY_SIZE="30"
export COLD_AI_TOOL_LOOP_WARNING_THRESHOLD="6"
export COLD_AI_TOOL_LOOP_CRITICAL_THRESHOLD="10"
```

Telegram optional env vars:

```bash
export COLD_AI_TELEGRAM_BOT_TOKEN="..."
export COLD_AI_TELEGRAM_DEFAULT_CHAT_ID="..."
```

## Phase 1.1: Web Review UI

You can review/approve/reject drafts in a React dashboard instead of CSV.

```bash
PYTHONPATH=src .venv/bin/python -m cold_ai.cli review-ui --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` (global start page). Authenticated app is at `/app`.

`review-ui` now auto-frees a busy port by default. To disable this behavior:

```bash
PYTHONPATH=src .venv/bin/python -m cold_ai.cli review-ui --host 127.0.0.1 --port 8000 --no-auto-free-port
```

Health check endpoint:

```bash
curl http://127.0.0.1:8000/health
```

In the campaign page you can:

- approve and schedule drafts
- reject drafts
- trigger `send due` in dry-run or real mode
- generate drafts from the UI
- click draft cards to edit subject/body
- apply quick personalization snippets and save edits
- switch between `Grid`, `List`, and `Compact` draft views

From the main dashboard you can now create campaigns directly (no CLI required for this step), including campaign purpose.
Campaigns now support channels: `email` and `whatsapp`.

The app now includes sidebar navigation with dedicated tabs:

- `Campaigns`: create and manage outreach campaigns/drafts
- `Scripts`: store reusable outreach scripts
- `Descriptions`: store reusable product/service descriptions
- `Settings`: account and workspace preferences

Settings now includes AI Agent controls per user:

- provider selection (OpenClaw-style local-first matrix)
- LLM base URL
- API key (stored locally in SQLite for your local instance)
- model priority list
- role prompts for `search`, `routing`, `supervisor`, and `rewrite` agents
- toggles for AI web-research and AI rewrite behavior
- learned outreach memory panel (view top memory patterns, refresh, clear)

Supported providers in Settings:

- `openai`
- `openrouter`
- `groq`
- `together`
- `ollama` (local)
- `vllm` (local/self-hosted)
- `anthropic`
- `gemini`

Campaign and draft guardrails are enforced server-side:

- campaign name/subject/body length and normalization checks
- optional campaign purpose validation
- blocked-language filtering for campaign templates and manual draft edits

The dashboard is a rich client (React) served by FastAPI, using JSON API routes under `/api/*`.

## Auth (OAuth + email/password)

This app uses Authlib OAuth providers with session-based access control.

Set these env vars before running:

```bash
export COLD_AI_SESSION_SECRET="replace-with-long-random-secret"
export COLD_AI_APP_BASE_URL="http://127.0.0.1:8000"
export COLD_AI_SESSION_MAX_AGE_SECONDS="86400"

# Google OAuth (optional but recommended)
export COLD_AI_OAUTH_GOOGLE_CLIENT_ID="..."
export COLD_AI_OAUTH_GOOGLE_CLIENT_SECRET="..."
```

Sign-in options:

- Google OAuth
- Email/password sign-up and sign-in forms (built into the start page)

Email accounts can change password from the dashboard (`Change Password` button in top bar).

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

If you prefer not to install the local package entrypoint, you can run every command in source mode:

```bash
PYTHONPATH=src .venv/bin/python -m cold_ai.cli --help
```

## 2) Initialize database

```bash
cold-ai init-db
```

This creates a SQLite DB at `data/cold_ai.db`.

## 3) Import leads from CSV

Expected columns (aliases supported):

- email (`email`, `mail`)
- phone (`phone`, `telephone`, `tel`, `mobile`, `gsm`, `numero`, `numero de telephone`)
- full name (`full_name`, `name`, `doctor_name`)
- specialty (`specialty`, `speciality`, `specialite`)
- city (`city`, `ville`)
- address (`address`, `adresse`)

Rows with phone but no email are still imported for WhatsApp campaigns.

```bash
cold-ai import-leads --csv-path data/doctors.csv
```

## 4) Create a campaign from templates

```bash
cold-ai create-campaign \
  --name "Algeria Doctors Outreach" \
  --purpose "Book discovery calls with priority clinics" \
  --channel "email" \
  --subject-template templates/subject_default.txt \
  --body-template templates/body_default.txt
```

For WhatsApp campaigns, set `--channel "whatsapp"`.

## 5) Generate drafts

```bash
cold-ai generate-drafts --campaign-id 1 --limit 200
```

## 6) Export for manual approval

```bash
cold-ai export-approvals --campaign-id 1
```

This generates `data/exports/campaign_1_approvals.csv`.

Edit CSV columns:

- `approved` -> `yes` or `no`
- `scheduled_at` -> ISO datetime (e.g. `2026-02-26T09:30:00+01:00`)

## 7) Import approvals and schedule

```bash
cold-ai import-approvals --csv-path data/exports/campaign_1_approvals.csv
```

CSV approval remains available as a fallback flow.

## 8) Send due outreach

Dry-run:

```bash
cold-ai send-due --dry-run
```

SMTP mode:

```bash
export COLD_AI_SMTP_HOST="smtp.example.com"
export COLD_AI_SMTP_PORT="587"
export COLD_AI_SMTP_USER="user@example.com"
export COLD_AI_SMTP_PASSWORD="your-password"
export COLD_AI_SMTP_FROM="user@example.com"
export COLD_AI_SMTP_STARTTLS="true"

cold-ai send-due
```

Notes for WhatsApp:

- `dry-run` is supported and prints WhatsApp deliveries to console.
- real WhatsApp provider integration is not configured yet, so real mode currently fails safely for WhatsApp drafts.

## Notes

- Phase 1 is intentionally human-in-the-loop before sending.
- Follow-ups, analytics, and advanced enrichment are Phase 2+.
- OSS-inspired architecture references are in `docs/OSS_REFERENCES.md`.
