from __future__ import annotations

import json
from datetime import datetime, timezone

from .db import get_connection


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LeadRepository:
    def upsert_many(self, leads: list[dict]) -> tuple[int, int]:
        inserted = 0
        skipped = 0
        with get_connection() as conn:
            for lead in leads:
                try:
                    conn.execute(
                        """
                        INSERT INTO leads (full_name, first_name, last_name, email, specialty, city, address, source_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            lead.get("full_name"),
                            lead.get("first_name"),
                            lead.get("last_name"),
                            lead["email"],
                            lead.get("specialty"),
                            lead.get("city"),
                            lead.get("address"),
                            lead.get("source_hash"),
                        ),
                    )
                    inserted += 1
                except Exception:
                    skipped += 1
        return inserted, skipped

    def list_for_drafting(self, limit: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT l.*
                FROM leads l
                ORDER BY l.id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, lead_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return dict(row) if row else None


class CampaignRepository:
    def create(self, name: str, subject_template: str, body_template: str) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO campaigns (name, subject_template, body_template)
                VALUES (?, ?, ?)
                """,
                (name, subject_template, body_template),
            )
            return int(cursor.lastrowid)

    def get(self, campaign_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM campaigns
                ORDER BY id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]


class DraftRepository:
    def create_or_ignore(self, campaign_id: int, lead_id: int, subject: str, body: str) -> bool:
        with get_connection() as conn:
            result = conn.execute(
                """
                INSERT OR IGNORE INTO drafts (campaign_id, lead_id, subject, body, status)
                VALUES (?, ?, ?, ?, 'draft')
                """,
                (campaign_id, lead_id, subject, body),
            )
            return result.rowcount > 0

    def list_for_campaign(self, campaign_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT d.*, l.email, l.full_name, l.specialty, l.city
                FROM drafts d
                JOIN leads l ON l.id = d.lead_id
                WHERE d.campaign_id = ?
                ORDER BY d.id ASC
                """,
                (campaign_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def approve_and_schedule(self, draft_id: int, scheduled_at: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE drafts
                SET status = 'approved', approved_at = ?, scheduled_at = ?
                WHERE id = ?
                """,
                (utc_now_iso(), scheduled_at, draft_id),
            )

    def mark_rejected(self, draft_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE drafts SET status = 'rejected' WHERE id = ?",
                (draft_id,),
            )

    def update_content(self, draft_id: int, subject: str, body: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE drafts
                SET subject = ?, body = ?
                WHERE id = ?
                """,
                (subject, body, draft_id),
            )

    def list_due(self, now_iso: str) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT d.*, l.email
                FROM drafts d
                JOIN leads l ON l.id = d.lead_id
                WHERE d.status = 'approved'
                  AND d.scheduled_at IS NOT NULL
                  AND d.scheduled_at <= ?
                ORDER BY d.scheduled_at ASC
                """,
                (now_iso,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_sent(self, draft_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE drafts
                SET status = 'sent', sent_at = ?, error_message = NULL
                WHERE id = ?
                """,
                (utc_now_iso(), draft_id),
            )

    def mark_failed(self, draft_id: int, error: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE drafts
                SET status = 'failed', error_message = ?
                WHERE id = ?
                """,
                (error[:1000], draft_id),
            )


class EventRepository:
    def log(self, event_type: str, payload: dict, draft_id: int | None = None) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO events (draft_id, event_type, payload)
                VALUES (?, ?, ?)
                """,
                (draft_id, event_type, json.dumps(payload, ensure_ascii=False)),
            )


class UserRepository:
    def create(self, email: str, password_hash: str, full_name: str | None = None) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (email, password_hash, full_name)
                VALUES (?, ?, ?)
                """,
                (email, password_hash, full_name),
            )
            return int(cursor.lastrowid)

    def get_by_email(self, email: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE lower(email) = lower(?)",
                (email,),
            ).fetchone()
        return dict(row) if row else None

    def get_by_id(self, user_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
