from django.contrib.gis import admin
from import_export.admin import ExportMixin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter

from analysis.models import GenericMeasurement
from prototype.mixins import (
    HybridProjectPermissionMixin,
    NestedProjectPermissionMixin,
    ProjectBasedPermissionMixin,
)

from .models import Campaign, ExposureType, Layer, Location, Sample, SampleType, Site, StudyArea, Tag
from .resources import LocationResource


class MeasurementInline(admin.TabularInline):
    model = GenericMeasurement
    extra = 1
    readonly_fields = (
        "method",
        "value",
        "parameter",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("method", "parameter")


class SampleTabularInline(TabularInline):
    model = Sample
    tab = True
    extra = 1
    show_change_link = True
    fields = [
        "identifier",
        "depth_top",
        "depth_bottom",
    ]

class SiteStackedInline(StackedInline):
    model = Site
    tab = True
    fields = [
        "label",
    ]
    extra = 1


class LayerTabularInline(TabularInline):
    model = Layer
    tab = True
    extra = 1
    fieldsets = (
        (
            "Identifier",
            {
                "classes": ["tab"],
                "fields": (
                    "identifier",
                    "token",
                ),
            },
        ),
        (
            "Parameter",
            {
                "classes": ["tab"],
                "fields": (
                    "depth_top",
                    "depth_bottom",
                    "structure",
                    "fine_soil_field",
                    "calcite",
                    "secondary_calcite",
                ),
            },
        ),
        (
            "Munsell Color",
            {
                "classes": ["tab"],
                "fields": (
                    "munsell_hue_value",
                    "munsell_hue",
                    "munsell_value",
                    "munsell_chroma",
                ),
            },
        ),
    )


class ExposureTypeAdmin(ExportMixin, ModelAdmin):
    list_display = [
        "name_en",
        "name_ger",
        "main_type",
    ]
    list_filter = [
        (
            "main_type",
            ChoicesDropdownFilter,
        ),
    ]
    list_filter_sheet = False
    list_filter_submit = True


class LocationAdmin(ExportMixin, ModelAdmin, ProjectBasedPermissionMixin):
    list_per_page = 20
    resource_classes = [LocationResource]
    readonly_fields = ["id"]
    list_display = [
        "identifier",
        "data_source",
        "project",
        "reference",
        "campaign",
        "date_of_record",
    ]
    raw_id_fields = [
        "project",
        "reference",
        "campaign",
    ]
    list_filter = [
        (
            "data_source",
            ChoicesDropdownFilter,
        ),
        (
            "project",
            RelatedDropdownFilter,
        ),
        (
            "reference",
            RelatedDropdownFilter,
        ),
        (
            "campaign",
            RelatedDropdownFilter,
        ),
        (
            "date_of_record",
            RangeDateFilter,
        ),
    ]
    list_filter_sheet = False
    list_filter_submit = True

    inlines = [
        LayerTabularInline,
        SampleTabularInline,
    ]

    search_fields = ["identifier", "campaign"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("project", "campaign", "reference")
    fieldsets = (
        (
            "Metadata",
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    "data_source",
                    "project",
                    "reference",
                    "campaign",
                    "identifier",
                    "date_of_record",
                    "processor",
                ),
            },
        ),
        (
            "Spatial Metadata",
            {
                "classes": ["tab"],
                "fields": (
                    "easting",
                    "northing",
                    "altitude",
                    "srid",
                    "location",
                ),
            },
        ),
        (
            "Data Acquisiton",
            {
                "classes": ["tab"],
                "fields": (
                    "study_site",
                    "exposure_type",
                    "liner",
                    "sampling",
                ),
            },
        ),
        (
            "Landform and topography",
            {
                "classes": ["tab"],
                "fields": (
                    "gradient_upslope",
                    "gradient_downslope",
                    "slope_aspect",
                    "relief_description",
                ),
            },
        ),
        (
            "Climate and Weather",
            {
                "classes": ["tab"],
                "fields": (
                    "current_weather_conditions",
                    "past_weather_conditions",
                ),
            },
        ),
    )


class StudyAreaAdmin(ExportMixin, ModelAdmin, ProjectBasedPermissionMixin):
    list_display = [
        "label",
        "project",
        "province",
    ]
    list_filter = [
        ("climate_koeppen", ChoicesDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True
    fieldsets = (
        (
            "Data",
            {
                "fields": (
                    "label",
                    "project",
                    "province",
                    "geometry",
                    "climate_koeppen",
                    "ecozone_schultz",
                ),
            },
        ),
    )

    inlines = [SiteStackedInline]


class SiteAdmin(
    ExportMixin,
    ModelAdmin,
    admin.options.GeoModelAdminMixin,
    NestedProjectPermissionMixin,
):
    project_path = "study_area__project"
    list_display = [
        "label",
        "study_area",
    ]
    fieldsets = (
        (
            "Data",
            {
                "fields": (
                    "label",
                    "study_area",
                ),
            },
        ),
    )


class CampaignAdmin(ExportMixin, ModelAdmin, ProjectBasedPermissionMixin):
    list_display = [
        "id",
        "label",
        "project",
        "date_start",
        "date_end",
    ]
    list_filter = [
        ("project", RelatedDropdownFilter),
        (
            "date_start",
            RangeDateFilter,
        ),
        (
            "date_end",
            RangeDateFilter,
        ),
        ("destination_country", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True
    raw_id_fields = [
        "project",
        # "destination_country",
        # "study_areas",
    ]

    fieldsets = (
        (
            "Metadata",
            {
                "fields": (
                    "label",
                    "project",
                    "date_start",
                    "date_end",
                    "destination_country",
                    "study_areas",
                ),
            },
        ),
    )


class LayerAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    project_path = "location__project"
    list_display = [
        "location",
        "identifier",
        "depth_top",
        "depth_bottom",
    ]
    list_filter = [
        (
            "location__project",
            RelatedDropdownFilter,
        ),
        (
            "location",
            RelatedDropdownFilter,
        ),
    ]
    list_filter_sheet = False
    list_filter_submit = True


class SampleAdmin(ExportMixin, ModelAdmin, HybridProjectPermissionMixin):
    show_full_result_count = False
    fields = [
        "identifier",
        "igsn",
        "project",
        "location",
        "processor",
        "parent",
        "description",
        "depth_top",
        "depth_bottom",
        "type",
        "layer",
        "tags",
    ]

    search_fields = [
        "identifier",
        "location__identifier",
    ]

    filter_horizontal = ["tags"]
    list_display = [
        "identifier",
        "project",
        "location",
        "depth_mid",
    ]
    grouped = True
    group_by = ["project", "location"]

    raw_id_fields = [
        "project",
        "location",
    ]
    list_filter = [
        (
            "project",
            RelatedDropdownFilter,
        ),
        (
            "location__campaign",
            RelatedDropdownFilter,
        ),
        (
            "location",
            RelatedDropdownFilter,
        ),
    ]
    list_filter_sheet = False
    list_filter_submit = True

class SampleTypeAdmin(ExportMixin, ModelAdmin):
    list_display = [
        "word",
        "label",
    ]
    list_filter = []
    list_filter_sheet = False
    list_filter_submit = True


class TagAdmin(ExportMixin, ModelAdmin, ProjectBasedPermissionMixin):
    list_display = ["word", "content_type", "project"]
    search_fields = ["word"]
    ordering = ["word"]
    list_filter = [
        ("content_type", RelatedDropdownFilter),
        ("project", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True


admin.site.register(ExposureType, ExposureTypeAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(StudyArea, StudyAreaAdmin)
admin.site.register(Site, SiteAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Layer, LayerAdmin)
admin.site.register(Sample, SampleAdmin)
admin.site.register(SampleType, SampleTypeAdmin)
admin.site.register(Tag, TagAdmin)
