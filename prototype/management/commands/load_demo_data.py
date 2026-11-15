"""Management command: load_demo_data.

Creates the synthetic demo project, two demo accounts (demo_pi and
demo_viewer) and a few landform regions; see prototype/demo_data.py. Safe to
run repeatedly: existing demo data is kept, accounts and permissions are
refreshed. The Docker demo (compose.demo.yml) runs it on every start.

Usage:
    python manage.py load_demo_data [--password PW] [--reset] [--allow-without-debug]

The accounts get a known password, so the command refuses to run unless
DEBUG is on.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from prototype.demo_data import (
    PI_USERNAME,
    VIEWER_USERNAME,
    create_demo_data,
    reset_demo_data,
)

if TYPE_CHECKING:
    from django.core.management.base import CommandParser


class Command(BaseCommand):
    """Load synthetic demo data and demo accounts."""

    help = "Load synthetic demo data and demo accounts (for the Docker demo)."

    def add_arguments(self, parser: CommandParser) -> None:
        """Register the command options."""
        parser.add_argument(
            "--password",
            default=os.environ.get("CGDB_DEMO_PASSWORD", "demo"),
            help="Password for the demo accounts (default: $CGDB_DEMO_PASSWORD or 'demo').",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the demo data and accounts first, then create them again.",
        )
        parser.add_argument(
            "--allow-without-debug",
            action="store_true",
            help="Run even though DEBUG is off. The accounts have a known password.",
        )

    def handle(self, *_args: object, **options: object) -> None:
        """Create the demo data and report what exists."""
        if not settings.DEBUG and not options["allow_without_debug"]:
            msg = (
                "DEBUG is off. The demo accounts get a known password, so this "
                "command is meant for demo and development databases only. "
                "Pass --allow-without-debug to run it anyway."
            )
            raise CommandError(msg)
        if options["reset"]:
            reset_demo_data()
            self.stdout.write("Removed existing demo data.")
        result = create_demo_data(str(options["password"]))
        state = "Created" if result.created else "Demo data already present;"
        counts = ", ".join(f"{k}: {v}" for k, v in result.counts.items())
        self.stdout.write(self.style.SUCCESS(f"{state} {counts}."))
        self.stdout.write(f"Log in as {PI_USERNAME} or {VIEWER_USERNAME}.")
