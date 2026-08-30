"""tech debt LBG9, step 3 of 3: drop the free-text method_legacy column now
that 0007 has backfilled the method ForeignKey from it.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("laboratory", "0007_backfill_accessoryparameter_method"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="accessoryparameter",
            name="method_legacy",
        ),
    ]
