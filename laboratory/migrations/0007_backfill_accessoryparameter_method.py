"""tech debt LBG9, step 2 of 3: backfill AccessoryParameter.method (FK) from
the old free-text method_legacy value by case-insensitive Method.name match.

Rows whose text doesn't match any Method.name exactly (typos, since-renamed
methods - the exact referential-integrity gap this migration exists to
close) are left with method=NULL rather than guessed at; method_legacy
(0006) survives until 0008 specifically so an operator can inspect and
manually resolve any unmatched rows before it's dropped.
"""

from django.db import migrations


def backfill_method_fk(apps, schema_editor):
    AccessoryParameter = apps.get_model("laboratory", "AccessoryParameter")
    Method = apps.get_model("laboratory", "Method")

    methods_by_lower_name = {}
    for method in Method.objects.all():
        methods_by_lower_name.setdefault(method.name.lower(), method)

    for param in AccessoryParameter.objects.exclude(
        method_legacy=""
    ).exclude(method_legacy__isnull=True):
        match = methods_by_lower_name.get(param.method_legacy.strip().lower())
        if match is not None:
            param.method_id = match.pk
            param.save(update_fields=["method"])


def noop_reverse(apps, schema_editor):
    """Irreversible: method_legacy already holds the original text, so
    reversing the FK assignment has nothing further to do."""


class Migration(migrations.Migration):

    dependencies = [
        ("laboratory", "0006_accessoryparameter_method_fk"),
    ]

    operations = [
        migrations.RunPython(backfill_method_fk, noop_reverse),
    ]
