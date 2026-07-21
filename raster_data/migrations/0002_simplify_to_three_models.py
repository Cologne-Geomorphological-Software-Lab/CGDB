# Drop LabelRaster, SceneLabelPair, DatasetMembership, DatasetSceneMembership.
# Add n_classes/class_names to RasterScene. Replace through-M2M with plain M2M.

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("raster_data", "0001_initial"),
    ]

    operations = [
        # 1. Remove M2M fields that use the through tables
        migrations.RemoveField(
            model_name="rasterdataset",
            name="pairs",
        ),
        migrations.RemoveField(
            model_name="rasterdataset",
            name="scenes",
        ),
        # 2. Drop the through tables
        migrations.DeleteModel(name="DatasetMembership"),
        migrations.DeleteModel(name="DatasetSceneMembership"),
        # 3. Drop SceneLabelPair (has FK to LabelRaster — must go before LabelRaster)
        migrations.DeleteModel(name="SceneLabelPair"),
        # 4. Drop LabelRaster
        migrations.DeleteModel(name="LabelRaster"),
        # 5. Add classification fields to RasterScene
        migrations.AddField(
            model_name="rasterscene",
            name="n_classes",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text="Number of distinct classes — for classification rasters only.",
            ),
        ),
        migrations.AddField(
            model_name="rasterscene",
            name="class_names",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Ordered list of class names — for classification rasters only.",
            ),
        ),
        # 6. Remove sampling_seed from RasterDataset (ML concern, not data concern)
        migrations.RemoveField(
            model_name="rasterdataset",
            name="sampling_seed",
        ),
        # 7. Add plain M2M scenes (no through table, related_name matches final models.py)
        migrations.AddField(
            model_name="rasterdataset",
            name="scenes",
            field=models.ManyToManyField(
                blank=True,
                related_name="datasets",
                to="raster_data.rasterscene",
            ),
        ),
    ]
