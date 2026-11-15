"""Create the table of the database cache (settings.CACHES).

Done as a migration rather than a separate `createcachetable` step so that
every update path creates it: `manage.py deploy`, a plain `migrate`, and a
fresh local setup. createcachetable is idempotent and does nothing for
cache backends that don't use the database.
"""

from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps: object, schema_editor: object) -> None:  # noqa: ARG001 — RunPython signature
    """Create the cache table(s) configured in settings.CACHES."""
    call_command("createcachetable", verbosity=0)


class Migration(migrations.Migration):
    dependencies = [
        ("prototype", "0005_add_audit_fields_to_projectuserobjectpermission"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop),
    ]
