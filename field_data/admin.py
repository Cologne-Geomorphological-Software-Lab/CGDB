import re

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from import_export.admin import ExportMixin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import display

from prototype.mixins import (
    HybridProjectPermissionMixin,
    NestedProjectPermissionMixin,
    ProjectBasedPermissionMixin,
)

from .models import Campaign, ExposureType, Layer, Location, Sample, SampleType, Site, StudyArea, Tag, Transect
from .resources import LocationResource





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
    compressed_fields = True
    warn_unsaved_form = True
    readonly_fields = ["id", "created_at", "created_by", "modified_at", "updated_by"]
    list_display = ["label", "project", "province", "climate_koeppen", "ecozone_schultz"]
    search_fields = ["label", "project__title"]
    autocomplete_fields = ["project"]
    list_filter = [
        ("climate_koeppen", ChoicesDropdownFilter),
        ("ecozone_schultz", ChoicesDropdownFilter),
        ("project", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True
    inlines = [SiteStackedInline]

    fieldsets = (
        (
            "Study Area",
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    ("label", "project"),
                    "province",
                    ("climate_koeppen", "ecozone_schultz"),
                    ("created_by", "created_at"),
                    ("updated_by", "modified_at"),
                ),
            },
        ),
        (
            "Geometry",
            {
                "classes": ["tab"],
                "fields": ("geometry",),
            },
        ),
    )


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
    save_on_top = True
    change_form_show_cancel_button = True
    compressed_fields = True
    warn_unsaved_form = True
    list_per_page = 20
    readonly_fields = ["id", "created_at", "created_by", "modified_at", "updated_by"]
    list_display = [
        "label",
        "project",
        "date_start",
        "date_end",
        "destination_country",
        "colored_season",
    ]
    search_fields = ["label", "project__title"]
    raw_id_fields = ["project"]
    autocomplete_fields = ["study_areas"]
    list_filter = [
        ("project", RelatedDropdownFilter),
        ("date_start", RangeDateFilter),
        ("date_end", RangeDateFilter),
        ("destination_country", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True

    @display(
        label={
            "SP": "info",
            "SU": "warning",
            "AU": "danger",
            "WI": "default",
            "WS": "info",
            "DS": "warning",
            "NS": "default",
        },
        description="Season",
    )
    def colored_season(self, obj):
        return obj.season

    fieldsets = (
        (
            "Campaign",
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    ("label", "project"),
                    ("date_start", "date_end"),
                    ("destination_country", "season"),
                    ("created_by", "created_at"),
                    ("updated_by", "modified_at"),
                ),
            },
        ),
        (
            "Study Areas",
            {
                "classes": ["tab"],
                "fields": ("study_areas",),
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
    compressed_fields = True
    warn_unsaved_form = True
    show_full_result_count = False
    readonly_fields = ["id", "created_at", "created_by", "modified_at", "updated_by"]
    search_fields = ["identifier", "location__identifier"]
    autocomplete_fields = ["project", "location", "processor", "parent", "layer", "type"]
    list_display = ["identifier", "project", "location", "depth_mid"]
    inlines = []
    list_filter = [
        ("project", RelatedDropdownFilter),
        ("location__campaign", RelatedDropdownFilter),
        ("location", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True

    fieldsets = (
        (
            "Sample",
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    ("identifier", "igsn"),
                    ("project", "location"),
                    ("processor", "date"),
                    "parent",
                    ("created_by", "created_at"),
                    ("updated_by", "modified_at"),
                ),
            },
        ),
        (
            "Properties",
            {
                "classes": ["tab"],
                "fields": (
                    ("type", "material"),
                    ("depth_top", "depth_bottom"),
                    ("layer", "weight"),
                    "description",
                ),
            },
        ),
        (
            "Tags",
            {
                "classes": ["tab"],
                "fields": ("tags",),
            },
        ),
    )

    # Registry: (url_slug, model_import_path) — drives get_urls() without 18 delegates.
    _ANALYSIS_REGISTRY = [
        ("genericmeasurement", "analysis.models.GenericMeasurement"),
        ("grainsize", "analysis.models.GrainSize"),
        ("luminescencedating", "analysis.models.LuminescenceDating"),
        ("radiocarbondating", "analysis.models.RadiocarbonDating"),
        ("counting", "analysis.models.Counting"),
        ("microxrfmeasurement", "analysis.models.MicroXRFMeasurement"),
    ]

    def get_urls(self):
        from importlib import import_module

        def _load(dotted):
            mod, cls = dotted.rsplit(".", 1)
            return getattr(import_module(mod), cls)

        custom_urls = []
        for slug, model_path in self._ANALYSIS_REGISTRY:
            model_class = _load(model_path)
            prefix = f"field_data_sample_{slug}"

            def make_views(m):
                def cl_view(request, sample_pk):
                    return self._analysis_changelist_view(request, sample_pk, m)
                def add_view(request, sample_pk):
                    return self._analysis_add_view(request, sample_pk, m)
                def change_view(request, sample_pk, object_id):
                    return self._analysis_change_view(request, sample_pk, m, object_id)
                return cl_view, add_view, change_view

            cl_view, add_view, change_view = make_views(model_class)
            custom_urls += [
                path(f"<int:sample_pk>/{slug}/",
                     self.admin_site.admin_view(cl_view),
                     name=prefix),
                path(f"<int:sample_pk>/{slug}/add/",
                     self.admin_site.admin_view(add_view),
                     name=f"{prefix}_add"),
                path(f"<int:sample_pk>/{slug}/<path:object_id>/change/",
                     self.admin_site.admin_view(change_view),
                     name=f"{prefix}_change"),
            ]
        return custom_urls + super().get_urls()

    def _get_accessible_sample(self, request, sample_pk):
        """Return Sample if accessible; raise 404 if missing, 403 if forbidden."""
        get_object_or_404(Sample, pk=sample_pk)
        if not self.get_queryset(request).filter(pk=sample_pk).exists():
            raise PermissionDenied

    def _analysis_changelist_view(self, request, sample_pk, model_class):
        """Render an analysis model's changelist filtered for sample_pk."""
        self._get_accessible_sample(request, sample_pk)
        analysis_admin = self.admin_site._registry[model_class]

        # Inject the sample filter — changelist reads this from GET params
        mutable_get = request.GET.copy()
        mutable_get["sample__id__exact"] = str(sample_pk)
        request.GET = mutable_get

        response = analysis_admin.changelist_view(request)

        # get_preserved_filters() checks current_url == changelist_url — fails for
        # our custom sub-view URLs. Patch both the context variable AND cl.preserved_filters
        # (used by the empty-state template via {% include ... with preserved_filters=cl.preserved_filters %}).
        if hasattr(response, "context_data"):
            from urllib.parse import urlencode
            pf = urlencode({"_changelist_filters": f"sample__id__exact={sample_pk}"})
            response.context_data["preserved_filters"] = pf
            cl = response.context_data.get("cl")
            if cl is not None:
                cl.preserved_filters = pf

        return response

    # ------------------------------------------------------------------
    # Add-view helpers
    # ------------------------------------------------------------------

    def _analysis_add_view(self, request, sample_pk, model_class):
        self._get_accessible_sample(request, sample_pk)
        analysis_admin = self.admin_site._registry[model_class]
        mutable_get = request.GET.copy()
        mutable_get["sample"] = str(sample_pk)
        request.GET = mutable_get
        response = analysis_admin.add_view(request)
        if hasattr(response, "context_data"):
            from urllib.parse import urlencode
            response.context_data["preserved_filters"] = urlencode(
                {"_changelist_filters": f"sample__id__exact={sample_pk}"}
            )
        return response

    # ------------------------------------------------------------------
    # Change-view helpers
    # ------------------------------------------------------------------

    def _analysis_change_view(self, request, sample_pk, model_class, object_id):
        self._get_accessible_sample(request, sample_pk)
        analysis_admin = self.admin_site._registry[model_class]
        response = analysis_admin.change_view(request, str(object_id))
        if hasattr(response, "context_data"):
            from urllib.parse import urlencode
            response.context_data["preserved_filters"] = urlencode(
                {"_changelist_filters": f"sample__id__exact={sample_pk}"}
            )
        return response

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "tags":
            sample_ct = ContentType.objects.get_for_model(Sample)
            qs = Tag.objects.filter(content_type=sample_ct)
            object_id = request.resolver_match.kwargs.get("object_id")
            if object_id:
                try:
                    project_id = Sample.objects.values_list("project", flat=True).get(pk=object_id)
                    if project_id:
                        qs = qs.filter(project=project_id)
                except Sample.DoesNotExist:
                    pass
            kwargs["queryset"] = qs
        return super().formfield_for_manytomany(db_field, request, **kwargs)

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

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        app_label = request.GET.get("app_label")
        field_name = request.GET.get("field_name")
        model_name = request.GET.get("model_name")
        model_map = {"location": Location, "sample": Sample}
        if app_label == "field_data" and field_name == "tags" and model_name in model_map:
            model_class = model_map[model_name]
            queryset = queryset.filter(content_type=ContentType.objects.get_for_model(model_class))
            match = re.search(rf"/{model_name}/(\d+)/change/", request.META.get("HTTP_REFERER", ""))
            if match:
                try:
                    project_id = model_class.objects.values_list("project", flat=True).get(pk=match.group(1))
                    if project_id:
                        queryset = queryset.filter(project=project_id)
                except model_class.DoesNotExist:
                    pass
        return queryset, may_have_duplicates


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
