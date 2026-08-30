"""Management command: run the full deployment update sequence.

Wraps the previously fully-manual sequence of dependency sync, a frontend
build, `migrate`, `collectstatic`, and service restarts into one command,
with a pre-migrate database backup and post-restart health checks built in.
Still started by hand over SSH — no external trigger, no new credentials, no
change to who initiates a deploy. See "Updating an existing deployment" in
README.md for the manual step-by-step this replaces.

`git pull` is deliberately **not** part of this command — it's run
separately, beforehand, by whoever has git credentials for the remote. This
command needs `sudo` (for the database backup and the service restarts),
and `root` normally has no git credentials of its own; keeping `git pull`
out of this command avoids needing a deploy key for `root` at all.

The frontend build (`npm ci && npm run build` in frontend/) is a one-shot
step, not a persistent process — it compiles the map dashboard's Vite app to
static/dist/ and exits, the same shape as `uv sync` just before it. Node/npm
only need to be installed on the server as a build tool (like GDAL/PostGIS
already are); nothing Node-based keeps running afterward.

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
        "Runs the deployment update sequence (dependency sync, frontend "
        "build, migrate, collectstatic, service restarts), with a "
        "pre-migrate database backup and post-restart health checks. Run "
        "`git pull` yourself beforehand — this command doesn't do it."
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
        """Run the deploy sequence: backup, sync, build, migrate, restart, verify."""
        dry_run: bool = options["dry_run"]  # type: ignore[assignment]

        if not dry_run and not options["yes"] and not self._confirm():
            self.stdout.write("Aborted.")
            return

        self._check_clean_working_tree()
        backup_path = self._backup_database(dry_run=dry_run)

        self._run(["uv", "sync"], dry_run=dry_run)

        # See module docstring: one-shot build, not a running server.
        # collectstatic below needs this to have already run so it has
        # something fresh to collect.
        frontend_dir = Path(settings.BASE_DIR) / "frontend"
        self._run(["npm", "ci"], dry_run=dry_run, cwd=frontend_dir)
        self._run(["npm", "run", "build"], dry_run=dry_run, cwd=frontend_dir)

        self._migrate_and_collectstatic(
            dry_run=dry_run, backup_path=backup_path
        )

        services = self._restart_services(dry_run=dry_run)
        for service in services:
            self._health_check(service, dry_run=dry_run)

        self.stdout.write(
            self.style.SUCCESS(f"Deployment complete. Backup: {backup_path}")
        )

    def _migrate_and_collectstatic(
        self, *, dry_run: bool, backup_path: str
    ) -> None:
        """Run migrate + collectstatic, pointing at the pre-migrate backup on failure."""
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

    def _restart_services(self, *, dry_run: bool) -> list[str]:
        """Restart every installed service in _SERVICES, warning about any not set up here."""
        services = [s for s in _SERVICES if self._service_exists(s)]
        skipped = [s for s in _SERVICES if s not in services]
        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipping {', '.join(skipped)} — no systemd unit found "
                    "for it on this host (not installed/enabled here)."
                )
            )
        for service in services:
            self._run(
                ["sudo", "systemctl", "restart", service], dry_run=dry_run
            )
        return services

    def _confirm(self) -> bool:
        """Ask for interactive confirmation before any effectful step runs."""
        answer = input(
            "This will back up the database, build the frontend, migrate, "
            f"and restart {', '.join(_SERVICES)}. Continue? [y/N] "
        )
        return answer.strip().lower() == "y"

    def _check_clean_working_tree(self) -> None:
        """Abort if the working tree has uncommitted changes (e.g. an interrupted git pull)."""
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
                "Working tree has uncommitted changes — aborting deploy. "
                f"Commit, stash, or discard them first:\n{result.stdout}"
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

    def _run(
        self,
        cmd: list[str],
        *,
        dry_run: bool,
        cwd: Path | str | None = None,
    ) -> None:
        """Print, and unless dry_run, execute an OS-level deploy step."""
        printable = " ".join(cmd)
        if dry_run:
            self.stdout.write(f"==> Would run: {printable}")
            return
        self.stdout.write(f"==> {printable}")
        subprocess.run(  # noqa: S603 — fixed, code-defined argv; no user input
            cmd, check=True, cwd=cwd if cwd is not None else settings.BASE_DIR
        )

    def _service_exists(self, service: str) -> bool:
        """Check whether a systemd unit is actually defined on this host.

        `_SERVICES` is a fixed list, but not every optional component (e.g.
        the Dagster daemon — see README's "Data Orchestration (Optional)")
        is set up on every deployment. Restarting/health-checking a unit
        that was never installed here should be skipped, not a hard failure.
        """
        cmd = ["systemctl", "show", service, "--property=LoadState", "--value"]
        result = subprocess.run(  # noqa: S603 — fixed args, no user input
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() == "loaded"

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
