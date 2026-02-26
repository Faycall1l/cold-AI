from __future__ import annotations

from pathlib import Path

import typer

from .db import init_db
from .services.approval_service import export_approvals, import_approvals
from .services.campaign_service import create_campaign
from .services.draft_service import generate_drafts
from .services.import_service import import_leads
from .services.send_service import send_due

app = typer.Typer(help="cold-AI Phase 1 CLI")


@app.command("init-db")
def init_db_command() -> None:
    init_db()
    typer.echo("Database initialized")


@app.command("import-leads")
def import_leads_command(csv_path: Path = typer.Option(..., exists=True, readable=True)) -> None:
    inserted, skipped = import_leads(csv_path)
    typer.echo(f"Leads imported: {inserted}, skipped: {skipped}")


@app.command("create-campaign")
def create_campaign_command(
    name: str = typer.Option(...),
    subject_template: Path = typer.Option(..., exists=True, readable=True),
    body_template: Path = typer.Option(..., exists=True, readable=True),
) -> None:
    campaign_id = create_campaign(name, subject_template, body_template)
    typer.echo(f"Campaign created with id={campaign_id}")


@app.command("generate-drafts")
def generate_drafts_command(
    campaign_id: int = typer.Option(...),
    limit: int = typer.Option(100),
) -> None:
    created, ignored = generate_drafts(campaign_id, limit)
    typer.echo(f"Drafts generated: {created}, ignored: {ignored}")


@app.command("export-approvals")
def export_approvals_command(campaign_id: int = typer.Option(...)) -> None:
    file_path = export_approvals(campaign_id)
    typer.echo(f"Approval file exported: {file_path}")


@app.command("import-approvals")
def import_approvals_command(csv_path: Path = typer.Option(..., exists=True, readable=True)) -> None:
    approved, rejected = import_approvals(csv_path)
    typer.echo(f"Approvals imported: approved={approved}, rejected={rejected}")


@app.command("send-due")
def send_due_command(dry_run: bool = typer.Option(False)) -> None:
    sent, failed = send_due(dry_run=dry_run)
    typer.echo(f"Send finished: sent={sent}, failed={failed}")


if __name__ == "__main__":
    app()
