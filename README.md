# cold-AI (Phase 1)

Phase 1 MVP of an agentic cold outreach system focused on:

- Importing leads from CSV
- Generating personalized drafts from templates
- Manual review and approval
- Scheduling
- Sending due emails (dry-run or SMTP)

## Personalization Engine (Phase 1.2)

Draft generation now follows a multi-step agent flow:

1. lead intelligence normalization
2. specialty template routing
3. optional web research snippet lookup
4. deterministic template drafting
5. optional LLM rewrite pass with quality gate
6. fallback to deterministic draft if rewrite confidence is low or provider fails

### Optional environment flags

```bash
export COLD_AI_ENABLE_WEB_RESEARCH="true"
export COLD_AI_ENABLE_LLM_REWRITE="true"

export COLD_AI_LLM_API_KEY="..."
export COLD_AI_LLM_BASE_URL="https://api.openai.com/v1"
export COLD_AI_LLM_MODELS="gpt-4o-mini,gpt-4.1-mini"
```

If `COLD_AI_ENABLE_LLM_REWRITE=false` or no API key is set, drafts are still generated via deterministic templates.

## Phase 1.1: Web Review UI

You can review/approve/reject drafts in a React dashboard instead of CSV.

```bash
PYTHONPATH=src .venv/bin/python -m cold_ai.cli review-ui --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` (global start page). Authenticated app is at `/app`.

In the campaign page you can:

- approve and schedule drafts
- reject drafts
- trigger `send due` in dry-run or real mode
- generate drafts from the UI
- click draft cards to edit subject/body
- apply quick personalization snippets and save edits
- switch between `Grid`, `List`, and `Compact` draft views

From the main dashboard you can now create campaigns directly (no CLI required for this step), including campaign purpose.

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

# Google OAuth (optional but recommended)
export COLD_AI_OAUTH_GOOGLE_CLIENT_ID="..."
export COLD_AI_OAUTH_GOOGLE_CLIENT_SECRET="..."
```

Sign-in options:

- Google OAuth
- Email/password sign-up and sign-in forms (built into the start page)

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
- full name (`full_name`, `name`, `doctor_name`)
- specialty (`specialty`, `speciality`, `specialite`)
- city (`city`, `ville`)
- address (`address`, `adresse`)

```bash
cold-ai import-leads --csv-path data/doctors.csv
```

## 4) Create a campaign from templates

```bash
cold-ai create-campaign \
  --name "Algeria Doctors Outreach" \
  --purpose "Book discovery calls with priority clinics" \
  --subject-template templates/subject_default.txt \
  --body-template templates/body_default.txt
```

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

## 8) Send due emails

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

## Notes

- Phase 1 is intentionally human-in-the-loop before sending.
- Follow-ups, analytics, and advanced enrichment are Phase 2+.
- OSS-inspired architecture references are in `docs/OSS_REFERENCES.md`.
