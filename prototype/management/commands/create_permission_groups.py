"""Management command: create_permission_groups.

Creates predefined Django Groups that bundle related permissions so users
can be granted access in one step instead of selecting individual permissions.

The actual group definitions live in prototype/permissions.py and are also
applied automatically after every `manage.py migrate` via a post_migrate signal.
Use this command with --reset when you need to rebuild groups from scratch.

Usage:
    python manage.py create_permission_groups [--reset]

    --reset  Clears all permissions from each group before re-adding.
             Safe to re-run after adding new models or renaming permissions.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from prototype.permissions import create_permission_groups


class Command(BaseCommand):
    """Management command that creates or resets predefined permission groups."""

    help = "Create predefined permission groups for CGDB."

    def add_arguments(self, parser: object) -> None:
        """Register the --reset flag on the argument parser."""
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear all permissions from each group before re-adding them.",
        )

    def handle(self, *_args: object, **options: object) -> None:
        """Execute the command, optionally resetting groups before rebuilding."""
        create_permission_groups(
            reset=options["reset"],
            stdout=self.stdout,
        )
