from django.contrib.contenttypes.models import ContentType
from django.contrib.gis import admin
from import_export.admin import ExportMixin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import display

from analysis.models import GenericMeasurement
from prototype.mixins import (
    HybridProjectPermissionMixin,
    NestedProjectPermissionMixin,
    ProjectBasedPermissionMixin,
)

from .models import Campaign, ExposureType, Layer, Location, Sample, SampleType, Site, StudyArea, Tag, Transect
from .resources import LocationResource


class MeasurementInline(admin.TabularInline):
    model = GenericMeasurement
    extra = 0
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
    extra = 0
    show_change_link = True
    fields = [
        "identifier",
        "depth_top",
        "depth_bottom",
        "type",
        "description",
    ]


class SiteStackedInline(StackedInline):
    model = Site
    tab = True
    fields = [
        "label",
    ]
    extra = 0


class LayerStackedInline(StackedInline):
    model = Layer
    tab = True
    extra = 0
    show_change_link = True
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("identifier", "token"),
                    ("depth_top", "depth_bottom"),
                ),
            },
        ),
        (
            "Properties",
            {
                "fields": (
                    ("structure", "fine_soil_field"),
                    ("calcite", "secondary_calcite"),
                ),
            },
        ),
        (
            "Munsell Color",
            {
                "fields": (
                    ("munsell_hue_value", "munsell_hue"),
                    ("munsell_value", "munsell_chroma"),
                ),
            },
        ),
    )


class ExposureTypeAdmin(ExportMixin, ModelAdmin):
    change_form_show_cancel_button = True
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
    save_on_top = True
    change_form_show_cancel_button = True
    compressed_fields = True
    warn_unsaved_form = True
    list_per_page = 20
    resource_classes = [LocationResource]
    readonly_fields = ["id", "created_at", "created_by", "modified_at", "updated_by"]
    list_display = [
        "identifier",
        "colored_data_source",
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
    autocomplete_fields = ["tags"]
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
        LayerStackedInline,
        SampleTabularInline,
    ]

    search_fields = ["identifier", "campaign__label"]

    @display(label={"internal": "success", "literature": "info"}, description="Data Source")
    def colored_data_source(self, obj):
        return obj.data_source

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("project", "campaign", "reference")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "tags":
            location_ct = ContentType.objects.get_for_model(Location)
            qs = Tag.objects.filter(content_type=location_ct)
            object_id = request.resolver_match.kwargs.get("object_id")
            if object_id:
                try:
                    project = Location.objects.values_list("project", flat=True).get(pk=object_id)
                    if project:
                        qs = qs.filter(project=project)
                except Location.DoesNotExist:
                    pass
            kwargs["queryset"] = qs
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    fieldsets = (
        (
            "Identification",
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    ("identifier", "data_source"),
                    ("project", "reference"),
                    ("campaign", "date_of_record"),
                    "processor",
                    "tags",
                    ("created_by", "created_at"),
                    ("updated_by", "modified_at"),
                ),
            },
        ),
        (
            "Coordinates",
            {
                "classes": ["tab"],
                "fields": (
                    ("easting", "northing"),
                    ("altitude", "srid"),
                    "location",
                ),
            },
        ),
        (
            "Field Setting",
            {
                "classes": ["tab"],
                "fields": (
                    ("study_site", "transect"),
                    "exposure_type",
                    ("liner", "sampling"),
                ),
            },
        ),
        (
            "Topography",
            {
                "classes": ["tab"],
                "fields": (
                    ("gradient_upslope", "gradient_downslope"),
                    "slope_aspect",
                    "relief_description",
                ),
            },
        ),
        (
            "Weather",
            {
                "classes": ["tab"],
                "fields": (
                    ("current_weather_conditions", "past_weather_conditions"),
                ),
            },
        ),
    )


class StudyAreaAdmin(ExportMixin, ModelAdmin, ProjectBasedPermissionMixin):
    save_on_top = True
    change_form_show_cancel_button = True
    list_display = [
        "label",
        "project",
        "province",
    ]
    search_fields = ["label", "project__title"]
    list_filter = [
        ("climate_koeppen", ChoicesDropdownFilter),
        ("project", RelatedDropdownFilter),
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
    change_form_show_cancel_button = True
    project_path = "study_area__project"
    list_display = [
        "label",
        "study_area",
    ]
    search_fields = ["label", "study_area__label"]
    list_filter = [
        ("study_area", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True
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
    change_form_show_cancel_button = True
    list_display = [
        "id",
        "label",
        "project",
        "date_start",
        "date_end",
    ]
    search_fields = ["label", "project__title"]
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
    raw_id_fields = ["project"]

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
    change_form_show_cancel_button = True
    project_path = "location__project"
    list_display = [
        "location",
        "identifier",
        "depth_top",
        "depth_bottom",
    ]
    search_fields = ["identifier", "location__identifier"]
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
    readonly_fields = ["created_at", "created_by", "modified_at", "updated_by"]


class SampleAdmin(ExportMixin, ModelAdmin, HybridProjectPermissionMixin):
    save_on_top = True
    change_form_show_cancel_button = True
    show_full_result_count = False
    readonly_fields = ["created_at", "created_by", "modified_at", "updated_by"]
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
        "created_by",
        "created_at",
        "updated_by",
        "modified_at",
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
    change_form_show_cancel_button = True
    list_display = [
        "word",
        "label",
    ]
    search_fields = ["word", "label"]
    ordering = ["word"]
    list_filter = []
    list_filter_sheet = False
    list_filter_submit = True


class TagAdmin(ExportMixin, ModelAdmin, ProjectBasedPermissionMixin):
    change_form_show_cancel_button = True
    list_display = ["word", "content_type", "project"]
    search_fields = ["word"]
    ordering = ["word"]
    list_filter = [
        ("content_type", RelatedDropdownFilter),
        ("project", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True


class TransectAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    change_form_show_cancel_button = True
    project_path = "study_area__project"
    list_display = ["identifier", "study_area", "campaign"]
    search_fields = ["identifier", "study_area__label"]
    list_filter = [
        ("study_area", RelatedDropdownFilter),
        ("campaign", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True
    raw_id_fields = ["study_area", "campaign"]


admin.site.register(ExposureType, ExposureTypeAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(StudyArea, StudyAreaAdmin)
admin.site.register(Site, SiteAdmin)
admin.site.register(Transect, TransectAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Layer, LayerAdmin)
admin.site.register(Sample, SampleAdmin)
admin.site.register(SampleType, SampleTypeAdmin)
admin.site.register(Tag, TagAdmin)
