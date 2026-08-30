"""Tests for the deploy management command."""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

_MAINT = "orchestration.dagster_home.maintenance_jobs"


def _proc(stdout: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, returncode=returncode)


def _subprocess_side_effect(
    *,
    dirty: bool = False,
    service_status: str = "active",
    service_exists: bool = True,
):
    """Return a subprocess.run stand-in that answers based on the argv it's given."""

    def _side_effect(cmd, **_kwargs):
        if cmd[:2] == ["git", "status"]:
            return _proc(stdout="M some_file.py\n" if dirty else "")
        if cmd[:2] == ["systemctl", "show"]:
            return _proc(stdout="loaded" if service_exists else "not-found")
        if cmd[:2] == ["systemctl", "is-active"]:
            return _proc(stdout=service_status)
        return _proc()

    return _side_effect


class DeployCommandTests(TestCase):
    def test_full_sequence_runs_in_expected_order(self):
        """Backup, then sync, then migrate, then restarts, then health checks.

        git pull is deliberately not part of this command -- it's a
        separate manual step the operator runs beforehand with their own
        git credentials (see the deploy command's module docstring)."""
        order: list[str] = []
        subprocess_run = MagicMock(side_effect=_subprocess_side_effect())

        def _tracking_subprocess(cmd, **kwargs):
            if cmd[:2] == ["uv", "sync"]:
                order.append("uv sync")
            elif cmd[:2] == ["sudo", "systemctl"]:
                order.append(f"restart {cmd[-1]}")
            elif cmd[:2] == ["systemctl", "is-active"]:
                order.append(f"health-check {cmd[-1]}")
            return _subprocess_side_effect()(cmd, **kwargs)

        subprocess_run.side_effect = _tracking_subprocess

        def _backup_sqlite(log, db, output_dir, timestamp):
            order.append("backup")
            return f"{output_dir}/backup_{timestamp}.sqlite3.gz"

        def _tracking_call_command(name, *args, **kwargs):
            order.append(name)

        stdout_io, stderr_io = StringIO(), StringIO()
        with (
            patch(
                "prototype.management.commands.deploy.subprocess.run",
                subprocess_run,
            ),
            patch(
                "prototype.management.commands.deploy.call_command",
                side_effect=_tracking_call_command,
            ),
            patch("builtins.input", return_value="y"),
            patch(f"{_MAINT}._is_sqlite", return_value=True),
            patch(f"{_MAINT}._backup_sqlite", side_effect=_backup_sqlite),
        ):
            call_command("deploy", stdout=stdout_io, stderr=stderr_io)

        assert order == [
            "backup",
            "uv sync",
            "migrate",
            "collectstatic",
            "restart apache2",
            "restart cgdb-dagster-daemon",
            "health-check apache2",
            "health-check cgdb-dagster-daemon",
        ]
        assert "Deployment complete" in stdout_io.getvalue()

    def test_yes_skips_confirmation_prompt(self):
        subprocess_run = MagicMock(side_effect=_subprocess_side_effect())
        with (
            patch(
                "prototype.management.commands.deploy.subprocess.run",
                subprocess_run,
            ),
            patch("prototype.management.commands.deploy.call_command"),
            patch("builtins.input") as mock_input,
            patch(f"{_MAINT}._is_sqlite", return_value=True),
            patch(f"{_MAINT}._backup_sqlite", return_value="backup.gz"),
        ):
            call_command("deploy", "--yes", stdout=StringIO(), stderr=StringIO())

        mock_input.assert_not_called()

    def test_declining_confirmation_aborts_before_any_effect(self):
        stdout_io, stderr_io = StringIO(), StringIO()
        subprocess_run = MagicMock(side_effect=_subprocess_side_effect())

        with (
            patch(
                "prototype.management.commands.deploy.subprocess.run",
                subprocess_run,
            ),
            patch(
                "prototype.management.commands.deploy.call_command"
            ) as mock_call_command,
            patch("builtins.input", return_value="n"),
        ):
            call_command("deploy", stdout=stdout_io, stderr=stderr_io)

        subprocess_run.assert_not_called()
        mock_call_command.assert_not_called()
        assert "Aborted" in stdout_io.getvalue()

    def test_dry_run_executes_no_effectful_step(self):
        stdout_io, stderr_io = StringIO(), StringIO()
        subprocess_run = MagicMock(side_effect=_subprocess_side_effect())

        with (
            patch(
                "prototype.management.commands.deploy.subprocess.run",
                subprocess_run,
            ),
            patch(
                "prototype.management.commands.deploy.call_command"
            ) as mock_call_command,
            patch("builtins.input") as mock_input,
        ):
            call_command("deploy", "--dry-run", stdout=stdout_io, stderr=stderr_io)

        mock_input.assert_not_called()
        mock_call_command.assert_not_called()
        # Only read-only checks run for real in dry-run mode: the
        # working-tree check and the per-service systemd LoadState probe
        # (needed to decide what to skip -- see _service_exists). Nothing
        # effectful (restarts, uv sync, npm build) actually executes.
        effectful_calls = [
            c
            for c in subprocess_run.call_args_list
            if c.args[0][:2] not in (["git", "status"], ["systemctl", "show"])
        ]
        assert effectful_calls == []
        stdout = stdout_io.getvalue()
        assert "Would run: uv sync" in stdout
        assert "Would run: sudo systemctl restart apache2" in stdout
        assert "Would check apache2 is active" in stdout

    def test_dirty_working_tree_aborts_before_backup(self):
        stdout_io, stderr_io = StringIO(), StringIO()
        subprocess_run = MagicMock(
            side_effect=_subprocess_side_effect(dirty=True)
        )

        with (
            patch(
                "prototype.management.commands.deploy.subprocess.run",
                subprocess_run,
            ),
            patch("builtins.input", return_value="y"),
            patch(f"{_MAINT}._is_sqlite", return_value=True),
            patch(f"{_MAINT}._backup_sqlite") as mock_backup_sqlite,
        ):
            with self.assertRaises(CommandError):
                call_command("deploy", stdout=stdout_io, stderr=stderr_io)

        mock_backup_sqlite.assert_not_called()

    def test_migration_failure_reports_backup_path_and_skips_restarts(self):
        stdout_io, stderr_io = StringIO(), StringIO()
        subprocess_run = MagicMock(side_effect=_subprocess_side_effect())

        with (
            patch(
                "prototype.management.commands.deploy.subprocess.run",
                subprocess_run,
            ),
            patch(
                "prototype.management.commands.deploy.call_command",
                side_effect=RuntimeError("migration exploded"),
            ),
            patch(f"{_MAINT}._is_sqlite", return_value=True),
            patch(
                f"{_MAINT}._backup_sqlite",
                return_value="/media/maintenance/backup_20260101_000000.sqlite3.gz",
            ),
        ):
            with self.assertRaises(RuntimeError):
                call_command("deploy", "--yes", stdout=stdout_io, stderr=stderr_io)

        stderr = stderr_io.getvalue()
        assert "Migration failed" in stderr
        assert "backup_20260101_000000.sqlite3.gz" in stderr
        restart_calls = [
            c
            for c in subprocess_run.call_args_list
            if c.args[0][:2] == ["sudo", "systemctl"]
        ]
        assert restart_calls == []

    def test_inactive_service_after_restart_is_reported(self):
        stdout_io, stderr_io = StringIO(), StringIO()
        subprocess_run = MagicMock(
            side_effect=_subprocess_side_effect(service_status="failed")
        )

        with (
            patch(
                "prototype.management.commands.deploy.subprocess.run",
                subprocess_run,
            ),
            patch("prototype.management.commands.deploy.call_command"),
            patch("builtins.input", return_value="y"),
            patch(f"{_MAINT}._is_sqlite", return_value=True),
            patch(f"{_MAINT}._backup_sqlite", return_value="backup.gz"),
        ):
            call_command("deploy", stdout=stdout_io, stderr=stderr_io)

        stderr = stderr_io.getvalue()
        assert "apache2 is not active after restart" in stderr
        assert "cgdb-dagster-daemon is not active after restart" in stderr

    def test_missing_systemd_unit_is_skipped_not_fatal(self):
        """A service with no installed systemd unit (e.g. the optional
        Dagster daemon on a server that doesn't use it) is skipped with a
        warning instead of aborting the whole deploy."""
        stdout_io, stderr_io = StringIO(), StringIO()
        subprocess_run = MagicMock(
            side_effect=_subprocess_side_effect(service_exists=False)
        )

        with (
            patch(
                "prototype.management.commands.deploy.subprocess.run",
                subprocess_run,
            ),
            patch("prototype.management.commands.deploy.call_command"),
            patch("builtins.input", return_value="y"),
            patch(f"{_MAINT}._is_sqlite", return_value=True),
            patch(f"{_MAINT}._backup_sqlite", return_value="backup.gz"),
        ):
            call_command("deploy", stdout=stdout_io, stderr=stderr_io)

        stdout = stdout_io.getvalue()
        assert "Skipping apache2, cgdb-dagster-daemon" in stdout
        assert "no systemd unit found" in stdout
        assert "Deployment complete" in stdout
        restart_calls = [
            c
            for c in subprocess_run.call_args_list
            if c.args[0][:2] == ["sudo", "systemctl"]
        ]
        assert restart_calls == []

    def test_healthy_services_reported_active(self):
        stdout_io, stderr_io = StringIO(), StringIO()
        subprocess_run = MagicMock(side_effect=_subprocess_side_effect())

        with (
            patch(
                "prototype.management.commands.deploy.subprocess.run",
                subprocess_run,
            ),
            patch("prototype.management.commands.deploy.call_command"),
            patch("builtins.input", return_value="y"),
            patch(f"{_MAINT}._is_sqlite", return_value=True),
            patch(f"{_MAINT}._backup_sqlite", return_value="backup.gz"),
        ):
            call_command("deploy", stdout=stdout_io, stderr=stderr_io)

        stdout = stdout_io.getvalue()
        assert "apache2: active" in stdout
        assert "cgdb-dagster-daemon: active" in stdout
        assert stderr_io.getvalue() == ""
