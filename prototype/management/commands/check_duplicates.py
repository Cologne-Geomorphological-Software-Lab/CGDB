"""Management command: check_duplicates.

Lists records that break the uniqueness rules CGDB 2.1 enforces for new
input and 3.0 turns into database constraints (#256, #285): locations
that share an identifier within a project, and pollen counts that count
the same taxon twice within one counting. Run it before upgrading to 3.0
and resolve what it lists; MIGRATING.md refers to it.

Usage:
    python manage.py check_duplicates
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count


class Command(BaseCommand):
    """List locations and pollen counts that violate the 3.0 uniqueness rules."""

    help = "List locations and pollen counts that violate the 3.0 uniqueness rules."

    def handle(self, *_args: object, **_options: object) -> None:
        """Print one line per duplicate group and a summary."""
        from analysis.models import PollenCount
        from field_data.models import Location

        groups = 0
        locations = (
            Location.objects.values("project__label", "identifier")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
            .order_by("project__label", "identifier")
        )
        for row in locations:
            groups += 1
            self.stdout.write(
                f"Location {row['identifier']!r} appears {row['n']} times "
                f"in project {row['project__label']}."
            )
        counts = (
            PollenCount.objects.values("counting_id", "pollen__name")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
            .order_by("counting_id", "pollen__name")
        )
        for row in counts:
            groups += 1
            self.stdout.write(
                f"Taxon {row['pollen__name']} is counted {row['n']} times "
                f"in counting {row['counting_id']}."
            )
        if groups:
            self.stdout.write(
                self.style.WARNING(
                    f"{groups} duplicate group(s). Resolve them before "
                    "upgrading to 3.0."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("No duplicates found."))
