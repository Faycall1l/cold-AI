from __future__ import annotations

import smtplib
from email.message import EmailMessage

from ..config import settings


class EmailProvider:
    def send(self, to_email: str, subject: str, body: str) -> None:
        raise NotImplementedError


class ConsoleEmailProvider(EmailProvider):
    def send(self, to_email: str, subject: str, body: str) -> None:
        print("=" * 80)
        print(f"TO: {to_email}")
        print(f"SUBJECT: {subject}")
        print(body)
        print("=" * 80)


class SMTPEmailProvider(EmailProvider):
    def send(self, to_email: str, subject: str, body: str) -> None:
        if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.smtp_from]):
            raise ValueError("SMTP settings are incomplete. Set COLD_AI_SMTP_* environment variables.")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_starttls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
