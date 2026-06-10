"""Shared permission-group creation logic.

Called from both the post_migrate signal (automatic) and the
create_permission_groups management command (manual/reset).
"""

from django.contrib.auth.models import Group, Permission
from django.db.models import Q


def _q(*specs, actions=None) -> Q:
    """Build a Q-filter for the given model specs and actions.

    specs   - "app_label.model_name" strings
    actions - list of verbs; defaults to all four CRUD actions
    """
    if actions is None:
        actions = ["view", "add", "change", "delete"]
    q = Q()
    for spec in specs:
        app_label, model_name = spec.split(".")
        for action in actions:
            q |= Q(
                content_type__app_label=app_label,
                content_type__model=model_name,
                codename=f"{action}_{model_name}",
            )
    return q


_ALL_DOMAIN = [
    # Field data
    "field_data.location",
    "field_data.sample",
    "field_data.layer",
    "field_data.campaign",
    "field_data.studyarea",
    "field_data.site",
    "field_data.transect",
    "field_data.tag",
    "field_data.sampletype",
    "field_data.exposuretype",
    # Analysis
    "analysis.luminescencedating",
    "analysis.radiocarbondating",
    "analysis.grainsize",
    "analysis.counting",
    "analysis.pollen",
    "analysis.rawmeasurement",
    "analysis.rawprocessing",
    "analysis.genericmeasurement",
    "analysis.microxrfmeasurement",
    "analysis.parameter",
    "analysis.algorithm",
    "analysis.measurementseries",
    # Bibliography
    "bibliography.reference",
    "bibliography.author",
    "bibliography.referencekeyword",
    # Laboratory
    "laboratory.device",
    "laboratory.accessory",
    "laboratory.calibration",
    "laboratory.firmware",
    "laboratory.method",
    "laboratory.manufacturer",
    # Prototype (researchers/groups — projects via Guardian only)
    "prototype.researcher",
    "prototype.researchgroup",
]

GROUPS = {
    # ------------------------------------------------------------------
    # Academic roles — assign exactly one per user
    # ------------------------------------------------------------------
    "Viewer": _q(*_ALL_DOMAIN, actions=["view"]),
    "Researcher": _q(*_ALL_DOMAIN, actions=["view", "add", "change"]),
    "Principal Investigator": _q(*_ALL_DOMAIN),
    # ------------------------------------------------------------------
    # Domain groups — stack on top of the academic role
    # ------------------------------------------------------------------
    "Field Data": _q(
        "field_data.location",
        "field_data.sample",
        "field_data.layer",
        "field_data.campaign",
        "field_data.studyarea",
        "field_data.site",
        "field_data.transect",
        "field_data.tag",
    ),
    "Luminescence": _q(
        "analysis.luminescencedating",
        "analysis.rawmeasurement",
        "analysis.rawprocessing",
    ),
    "Radiocarbon": _q("analysis.radiocarbondating"),
    "Grain Size": _q("analysis.grainsize"),
    "Pollen": _q(
        "analysis.counting",
        "analysis.pollen",
    ),
    "Geochemistry": _q(
        "analysis.genericmeasurement",
        "analysis.microxrfmeasurement",
        "analysis.parameter",
    ),
    "Bibliography": _q(
        "bibliography.reference",
        "bibliography.author",
        "bibliography.referencekeyword",
    ),
    "Laboratory": _q(
        "laboratory.device",
        "laboratory.accessory",
        "laboratory.calibration",
        "laboratory.firmware",
        "laboratory.method",
        "laboratory.manufacturer",
    ),
}


def create_permission_groups(reset=False, stdout=None) -> tuple:
    """Create or update predefined permission groups. Idempotent.

    reset=True clears all permissions from each group before re-adding —
    use this after removing models or renaming permissions.

    Returns (created_count, updated_count).
    """
    created_count = 0
    updated_count = 0

    for group_name, perm_filter in GROUPS.items():
        group, created = Group.objects.get_or_create(name=group_name)

        if reset:
            group.permissions.clear()

        permissions = Permission.objects.filter(perm_filter)
        group.permissions.add(*permissions)

        if stdout:
            label = "Created" if created else "Updated"
            stdout.write(f"  {label:8s} '{group_name}' ({permissions.count()} permissions)\n")

        if created:
            created_count += 1
        else:
            updated_count += 1

    if stdout:
        stdout.write(f"\nDone. {created_count} group(s) created, {updated_count} group(s) updated.\n")

    return created_count, updated_count
