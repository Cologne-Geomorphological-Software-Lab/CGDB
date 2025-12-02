from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from prototype.models import Researcher

from .models import (
    Campaign,
    ExposureType,
    Layer,
    Location,
    Project,
    Province,
    Sample,
    StudyArea,
)


class LocationResource(resources.ModelResource):

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
    project = fields.Field(
        column_name="project",
        attribute="project",
        widget=ForeignKeyWidget(
            Project,
            field="name",
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
        model = StudyArea
        skip_unchanged = True
        report_skipped = True


class CampaignResource(resources.ModelResource):
    project = fields.Field(
        column_name="project",
        attribute="project",
        widget=ForeignKeyWidget(
            Project,
            field="name",
        ),
    )

    destination_country = fields.Field(
        column_name="destination_country",
        attribute="destination_country",
        widget=ForeignKeyWidget(
            Project,
            field="name",
        ),
    )

    class Meta:
        model = Campaign
        skip_unchanged = True
        report_skipped = True


class SampleResource(resources.ModelResource):
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
            "depth_mid",
            "parent",
            "layer",
            "description",
            "material",
            "label_a",
            "label_b",
            "label_c",
        )


class LayerResource(resources.ModelResource):
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
        model = Layer
        skip_unchanged = True
        report_skipped = True
