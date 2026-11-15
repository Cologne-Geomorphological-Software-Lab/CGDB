"""Where maintenance jobs write their results."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings


def maintenance_output_dir() -> Path:
    """Return the directory for backups, DuckDB exports and integrity reports.

    It lies in protected storage (prototype.storage), next to where
    MaintenanceRun.result_file expects its "maintenance/<name>" files: these
    files contain the whole database and must never be reachable through a
    web server's /media/ alias.
    """
    return Path(settings.PROTECTED_MEDIA_ROOT) / "maintenance"
