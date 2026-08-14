"""Import/export resource definitions for field_data models."""

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from .models import (
    Campaign,
    Country,
    ExposureType,
    Location,
    Project,
    Province,
    SampleType,
    Site,
    StudyArea,
)


class LocationResource(resources.ModelResource):
    """Import/export resource for the Location model."""

    exposure_type = fields.Field(
        column_name="exposure_type",
        attribute="exposure_type",
        widget=ForeignKeyWidget(ExposureType, field="name_en"),
    )
    campaign = fields.Field(
        column_name="campaign",
        attribute="campaign",
        widget=ForeignKeyWidget(Campaign, field="label"),
    )
    project = fields.Field(
        column_name="project",
        attribute="project",
        widget=ForeignKeyWidget(Project, field="pk"),
    )

    class Meta:
        """Resource metadata for LocationResource."""

        model = Location
        skip_unchanged = True
        report_skipped = True
        fields = (
            "id",
            "project",
            "altitude",
            "campaign",
            "current_weather_conditions",
            "date_of_record",
            "easting",
            "northing",
            "exposure_type",
            "gradient_downslope",
            "gradient_upslope",
            "identifier",
            "liner",
            "location",
            "past_weather_conditions",
            "relief_description",
            "sampling",
            "slope_aspect",
            "srid",
            "study_site",
            "transect",
        )


class CountryResource(resources.ModelResource):
    """Import/export resource for the Country model."""

    class Meta:
        """Resource metadata for CountryResource."""

        model = Country
        skip_unchanged = True
        report_skipped = True
        fields = ("id", "name", "iso_code")


class ProvinceResource(resources.ModelResource):
    """Import/export resource for the Province model."""

    country = fields.Field(
        column_name="country",
        attribute="country",
        widget=ForeignKeyWidget(Country, field="name"),
    )

    class Meta:
        """Resource metadata for ProvinceResource."""

        model = Province
        skip_unchanged = True
        report_skipped = True
        fields = ("id", "name", "country")


class ExposureTypeResource(resources.ModelResource):
    """Import/export resource for the ExposureType model."""

    class Meta:
        """Resource metadata for ExposureTypeResource."""

        model = ExposureType
        skip_unchanged = True
        report_skipped = True
        fields = ("id", "main_type", "abbreviation", "name_ger", "name_en")


class SampleTypeResource(resources.ModelResource):
    """Import/export resource for the SampleType model."""

    class Meta:
        """Resource metadata for SampleTypeResource."""

        model = SampleType
        skip_unchanged = True
        report_skipped = True
        fields = ("id", "word", "label")


class SiteResource(resources.ModelResource):
    """Import/export resource for the Site model."""

    study_area = fields.Field(
        column_name="study_area",
        attribute="study_area",
        widget=ForeignKeyWidget(StudyArea, field="label"),
    )

    class Meta:
        """Resource metadata for SiteResource."""

        model = Site
        skip_unchanged = True
        report_skipped = True
        fields = ("id", "label", "study_area")
