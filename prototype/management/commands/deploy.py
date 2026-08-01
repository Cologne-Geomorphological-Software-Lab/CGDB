"""Management command: run the full deployment update sequence.

Wraps the previously fully-manual sequence of `git pull`, dependency sync,
`migrate`, `collectstatic`, and service restarts into one command, with a
pre-migrate database backup and post-restart health checks built in. Still
started by hand over SSH — no external trigger, no new credentials, no
change to who initiates a deploy. See "Updating an existing deployment" in
README.md for the manual step-by-step this replaces.

Usage:
    python manage.py deploy [--yes] [--dry-run]

    --yes       Skip the confirmation prompt.
    --dry-run   Print each step without executing it.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

if TYPE_CHECKING:
    from argparse import ArgumentParser

_SERVICES = ("apache2", "cgdb-dagster-daemon")


class Command(BaseCommand):
    """Run the deployment update sequence with a backup and health checks."""

    help = (
        "Runs the full deployment update sequence (git pull, dependency "
        "sync, migrate, collectstatic, service restarts), with a "
        "pre-migrate database backup and post-restart health checks."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Register --yes and --dry-run flags on the argument parser."""
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip the confirmation prompt.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print each step without executing it.",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Run the deploy sequence: backup, pull, sync, migrate, restart, verify."""
        dry_run: bool = options["dry_run"]  # type: ignore[assignment]

        if not dry_run and not options["yes"] and not self._confirm():
            self.stdout.write("Aborted.")
            return

        self._check_clean_working_tree()
        backup_path = self._backup_database(dry_run=dry_run)

        self._run(["git", "pull", "--ff-only"], dry_run=dry_run)
        self._run(["uv", "sync"], dry_run=dry_run)

        try:
            if dry_run:
                self.stdout.write("==> Would run: manage.py migrate --noinput")
                self.stdout.write(
                    "==> Would run: manage.py collectstatic --noinput"
                )
            else:
                call_command("migrate", "--noinput")
                call_command("collectstatic", "--noinput")
        except Exception:
            self.stderr.write(
                self.style.ERROR(
                    f"Migration failed. Pre-migrate backup is at "
                    f"{backup_path} — review it before deciding whether to "
                    "restore."
                )
            )
            raise

        for service in _SERVICES:
            self._run(
                ["sudo", "systemctl", "restart", service], dry_run=dry_run
            )

        for service in _SERVICES:
            self._health_check(service, dry_run=dry_run)

        self.stdout.write(
            self.style.SUCCESS(f"Deployment complete. Backup: {backup_path}")
        )

    def _confirm(self) -> bool:
        """Ask for interactive confirmation before any effectful step runs."""
        answer = input(
            "This will pull new code, back up the database, migrate, and "
            f"restart {', '.join(_SERVICES)}. Continue? [y/N] "
        )
        return answer.strip().lower() == "y"

    def _check_clean_working_tree(self) -> None:
        """Abort if local changes exist that `git pull --ff-only` could collide with."""
        cmd = ["git", "status", "--porcelain"]
        result = subprocess.run(  # noqa: S603 — fixed args, no user input
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=settings.BASE_DIR,
        )
        if result.stdout.strip():
            msg = (
                "Working tree has uncommitted changes — aborting before "
                f"`git pull`. Commit, stash, or discard them first:\n"
                f"{result.stdout}"
            )
            raise CommandError(msg)

    def _backup_database(self, *, dry_run: bool) -> str:
        """Back up the active database (SQLite or Postgres, auto-detected) before migrating.

        Reuses the same backup helpers the Dagster backup_job op uses
        (orchestration/dagster_home/maintenance_jobs.py), so backup logic
        lives in exactly one place regardless of which entry point runs it.
        """
        from orchestration.dagster_home.maintenance_jobs import (
            _backup_postgres,
            _backup_sqlite,
            _is_sqlite,
        )

        db = settings.DATABASES["default"]
        engine: str = db.get("ENGINE", "")
        output_dir = Path(settings.MEDIA_ROOT) / "maintenance"
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        if dry_run:
            kind = "SQLite" if _is_sqlite(engine) else "PostgreSQL"
            self.stdout.write(
                f"==> Would back up {kind} database to {output_dir}"
            )
            return "<dry-run: no backup written>"

        if _is_sqlite(engine):
            output_path = _backup_sqlite(
                self.stdout.write, db, str(output_dir), timestamp
            )
        else:
            output_path = _backup_postgres(
                self.stdout.write, db, str(output_dir), timestamp
            )

        self.stdout.write(f"Backup written to {output_path}")
        return str(output_path)

    def _run(self, cmd: list[str], *, dry_run: bool) -> None:
        """Print, and unless dry_run, execute an OS-level deploy step."""
        printable = " ".join(cmd)
        if dry_run:
            self.stdout.write(f"==> Would run: {printable}")
            return
        self.stdout.write(f"==> {printable}")
        subprocess.run(  # noqa: S603 — fixed, code-defined argv; no user input
            cmd, check=True, cwd=settings.BASE_DIR
        )

    def _health_check(self, service: str, *, dry_run: bool) -> None:
        """Confirm a service is actually active after being restarted.

        `systemctl restart` only reports that the restart command itself
        succeeded, not that the service stayed up afterward — a service that
        crashes immediately (e.g. an import error in the new code) would
        otherwise look like a successful deploy.
        """
        if dry_run:
            self.stdout.write(f"==> Would check {service} is active")
            return
        cmd = ["systemctl", "is-active", service]
        result = subprocess.run(  # noqa: S603 — fixed args, no user input
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        status = result.stdout.strip()
        if status == "active":
            self.stdout.write(f"{service}: active")
        else:
            self.stderr.write(
                self.style.ERROR(
                    f"{service} is not active after restart (status: "
                    f"{status!r}). Check its logs before assuming the "
                    "deployment succeeded."
                )
            )
