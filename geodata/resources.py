"""Import/export resource definitions for geodata models."""

from import_export import resources

from .models import Landform


class LandformResource(resources.ModelResource):
    """Import/export resource for the Landform model."""

    class Meta:
        """Resource metadata for LandformResource."""

        model = Landform
        skip_unchanged = True
        report_skipped = True
        exclude = ("geometry",)
