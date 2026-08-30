"""tech debt LBG9: convert AccessoryParameter.method from free-text CharField
to a ForeignKey(Method) with referential integrity.

Step 1 of 3: rename the existing text column out of the way (pure DB-level
rename, no data touched) and add the new FK column alongside it, nullable so
existing rows aren't blocked. 0007 backfills method from method_legacy by
matching Method.name; 0008 drops method_legacy once backfilled.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratory", "0005_alter_accessory_options_alter_device_options_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="accessoryparameter",
            old_name="method",
            new_name="method_legacy",
        ),
        migrations.AddField(
            model_name="accessoryparameter",
            name="method",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to="laboratory.method",
            ),
        ),
    ]
