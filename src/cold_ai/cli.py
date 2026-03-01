from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path

import typer

from .db import init_db
from .services.approval_service import export_approvals, import_approvals
from .services.campaign_service import create_campaign
from .services.draft_service import generate_drafts
from .services.import_service import import_leads
from .services.send_service import send_due
from .web.app import app as web_app

app = typer.Typer(help="cold-AI Phase 1 CLI")


def _port_is_busy(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def _free_port(port: int) -> int:
    if shutil.which("lsof") is None:
        return 0

    process = subprocess.run(
        ["lsof", "-ti", f"tcp:{port}"],
        check=False,
        capture_output=True,
        text=True,
    )
    pids = [line.strip() for line in process.stdout.splitlines() if line.strip()]
    killed = 0
    for pid in pids:
        if pid == str(os.getpid()):
            continue
        try:
            os.kill(int(pid), 9)
            killed += 1
        except Exception:
            continue
    return killed


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
    purpose: str = typer.Option(""),
    channel: str = typer.Option("email"),
) -> None:
    campaign_id = create_campaign(name, subject_template, body_template, purpose=purpose, channel=channel)
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


@app.command("review-ui")
def review_ui_command(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000),
    auto_free_port: bool = typer.Option(True, "--auto-free-port/--no-auto-free-port"),
) -> None:
    import uvicorn

    if _port_is_busy(host, port):
        if auto_free_port:
            killed = _free_port(port)
            if killed:
                typer.echo(f"Freed port {port} by terminating {killed} process(es)")
            else:
                typer.echo(
                    f"Port {port} is busy and no process was terminated automatically. "
                    "Retry with a different port or free it manually."
                )
        else:
            typer.echo(
                f"Port {port} is already in use. "
                "Use --auto-free-port or choose a different --port."
            )
            raise typer.Exit(code=1)

    uvicorn.run(web_app, host=host, port=port)


if __name__ == "__main__":
    app()
