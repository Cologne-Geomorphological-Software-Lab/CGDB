"""Import/export resource definitions for field_data models."""

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from prototype.models import Researcher

from .models import (
    Campaign,
    Country,
    ExposureType,
    Layer,
    Location,
    Project,
    Province,
    Sample,
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


class StudyAreaResource(resources.ModelResource):
    """Import/export resource for the StudyArea model."""

    project = fields.Field(
        column_name="project",
        attribute="project",
        widget=ForeignKeyWidget(
            Project,
            field="label",
        ),
    )

    province = fields.Field(
        column_name="province",
        attribute="province",
        widget=ForeignKeyWidget(
            Province,
            field="name",
        ),
    )

    class Meta:
        """Resource metadata for StudyAreaResource."""

        model = StudyArea
        skip_unchanged = True
        report_skipped = True


class CampaignResource(resources.ModelResource):
    """Import/export resource for the Campaign model."""

    project = fields.Field(
        column_name="project",
        attribute="project",
        widget=ForeignKeyWidget(
            Project,
            field="label",
        ),
    )

    destination_country = fields.Field(
        column_name="destination_country",
        attribute="destination_country",
        widget=ForeignKeyWidget(
            Country,
            field="name",
        ),
    )

    class Meta:
        """Resource metadata for CampaignResource."""

        model = Campaign
        skip_unchanged = True
        report_skipped = True


class SampleResource(resources.ModelResource):
    """Import/export resource for the Sample model."""

    location = fields.Field(
        column_name="location",
        attribute="location",
        widget=ForeignKeyWidget(
            Location,
            field="identifier",
        ),
    )

    processor = fields.Field(
        column_name="processor",
        attribute="processor",
        widget=ForeignKeyWidget(Researcher, field="user__last_name"),
    )

    class Meta:
        """Resource metadata for SampleResource."""

        model = Sample
        skip_unchanged = True
        report_skipped = True
        fields = (
            "identifier",
            "id",
            "location",
            "processor",
            "depth_top",
            "depth_bottom",
            "parent",
            "layer",
            "description",
            "material",
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


class LayerResource(resources.ModelResource):
    """Import/export resource for the Layer model."""

    location = fields.Field(
        column_name="location",
        attribute="location",
        widget=ForeignKeyWidget(
            Location,
            field="identifier",
        ),
    )

    processor = fields.Field(
        column_name="processor",
        attribute="processor",
        widget=ForeignKeyWidget(Researcher, field="user__last_name"),
    )

    class Meta:
        """Resource metadata for LayerResource."""

        model = Layer
        skip_unchanged = True
        report_skipped = True
