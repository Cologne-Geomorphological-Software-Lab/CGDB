"""Management command: move protected files out of MEDIA_ROOT.

Before 2.0.2, uploads (field photos, measurement files, rasters, …) and
maintenance results (database backups, exports) were stored under
MEDIA_ROOT, which a web server may serve without any login. Their FileFields
now use protected storage under PROTECTED_MEDIA_ROOT. This command moves the
existing files to the same relative paths there, so the stored names keep
working. `manage.py deploy` runs it after `migrate`.

Safe to run repeatedly: files already moved are not found again. A file
that already exists at the target with identical content (an interrupted
earlier run) only has its source removed. A target with different content
stops the command before it moves anything: nothing is overwritten.

Usage:
    python manage.py move_protected_media [--dry-run]
"""

from __future__ import annotations

import filecmp
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from prototype.protected_media import RULES

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    """Move files under protected upload prefixes from MEDIA_ROOT to PROTECTED_MEDIA_ROOT."""

    help = (
        "Moves uploads and maintenance results from MEDIA_ROOT to "
        "PROTECTED_MEDIA_ROOT (same relative paths). Never overwrites."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Register the --dry-run flag."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the files that would move without moving them.",
        )

    def handle(self, *args: object, **options: object) -> None:  # noqa: ARG002 — Django management command signature
        """Plan every move, refuse on conflicts, then move."""
        dry_run = bool(options["dry_run"])
        roots = self._roots()
        if roots is None:
            self.stdout.write("Nothing to move: MEDIA_ROOT does not exist.")
            return
        media_root, protected_root = roots
        self.stdout.write(f"From {media_root} to {protected_root}:")
        moves = self._plan(media_root, protected_root)
        self._refuse_conflicts(media_root, moves)
        if not moves:
            self.stdout.write("Nothing to move.")
            return
        for relative, target in moves:
            self.stdout.write(f"  {relative}")
            if not dry_run:
                self._move(media_root / relative, target)
        if dry_run:
            self.stdout.write(f"Would move {len(moves)} file(s).")
            return
        self._remove_empty_dirs(media_root)
        self.stdout.write(
            self.style.SUCCESS(
                f"Moved {len(moves)} file(s) to {protected_root}."
            )
        )

    @staticmethod
    def _roots() -> tuple[Path, Path] | None:
        """Return (MEDIA_ROOT, PROTECTED_MEDIA_ROOT), or None without media.

        Like Django's FileSystemStorage, an empty MEDIA_ROOT means uploads
        were stored relative to the current working directory.
        """
        media_root = Path(str(settings.MEDIA_ROOT or "")).resolve()
        protected_root = Path(str(settings.PROTECTED_MEDIA_ROOT)).resolve()
        if not media_root.is_dir():
            return None
        if media_root == protected_root:
            msg = "MEDIA_ROOT and PROTECTED_MEDIA_ROOT are the same directory."
            raise CommandError(msg)
        return media_root, protected_root

    @staticmethod
    def _refuse_conflicts(
        media_root: Path, moves: list[tuple[str, Path]]
    ) -> None:
        """Stop before moving anything if a target differs from its source."""
        conflicts = [
            relative
            for relative, target in moves
            if target.exists()
            and not filecmp.cmp(media_root / relative, target, shallow=False)
        ]
        if conflicts:
            msg = (
                "These files exist under both MEDIA_ROOT and "
                "PROTECTED_MEDIA_ROOT with different content; nothing was "
                "moved. Compare them and remove the wrong copy:\n  "
                + "\n  ".join(conflicts)
            )
            raise CommandError(msg)

    @staticmethod
    def _plan(
        media_root: Path, protected_root: Path
    ) -> list[tuple[str, Path]]:
        """Return (relative path, target) for every file under a protected prefix."""
        moves = []
        for prefix in sorted(RULES):
            source_dir = media_root / prefix
            if not source_dir.is_dir():
                continue
            for source in sorted(source_dir.rglob("*")):
                if source.is_file():
                    relative = source.relative_to(media_root).as_posix()
                    moves.append((relative, protected_root / relative))
        return moves

    @staticmethod
    def _move(source: Path, target: Path) -> None:
        """Move one file; an identical copy at the target only drops the source."""
        if target.exists():
            source.unlink()
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, target)

    @staticmethod
    def _remove_empty_dirs(media_root: Path) -> None:
        """Remove the protected prefix directories left empty under MEDIA_ROOT."""
        for prefix in RULES:
            top = media_root / prefix
            if not top.is_dir():
                continue
            # Deepest first, so parents are empty by the time they are checked.
            for directory in sorted(
                (p for p in top.rglob("*") if p.is_dir()), reverse=True
            ):
                if not any(directory.iterdir()):
                    directory.rmdir()
            current = top
            while current != media_root and not any(current.iterdir()):
                current.rmdir()
                current = current.parent
