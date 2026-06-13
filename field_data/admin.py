"""Django admin configuration for field_data models."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import path
from import_export.admin import ExportMixin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import display

from prototype.mixins import (
    HybridProjectPermissionMixin,
    NestedProjectPermissionMixin,
    ProjectBasedPermissionMixin,
)

from .models import (
    Campaign,
    ExposureType,
    Layer,
    Location,
    Sample,
    SampleType,
    Site,
    StudyArea,
    Tag,
    Transect,
)
from .resources import LocationResource

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import Field
    from django.http import HttpRequest, HttpResponse


class SampleTabularInline(TabularInline):
    """Tabular inline for Sample records nested under a Location."""

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
    """Stacked inline for Site records nested under a StudyArea."""

    model = Site
    tab = True
    fields = [
        "label",
    ]
    extra = 0


class LayerStackedInline(StackedInline):
    """Stacked inline for Layer records nested under a Location."""

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
    """Admin interface for ExposureType records."""

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


class TagFilterMixin:
    """Restrict the tags M2M dropdown to the current model's content type and project."""

    def formfield_for_manytomany(
        self,
        db_field: object,
        request: HttpRequest,
        **kwargs: object,
    ) -> Field | None:
        """Filter tag choices to the current model's content type and project."""
        if db_field.name == "tags":
            ct = ContentType.objects.get_for_model(self.model)
            qs = Tag.objects.filter(content_type=ct)
            object_id = request.resolver_match.kwargs.get("object_id")
            if object_id:
                try:
                    project = self.model.objects.values_list(
                        "project",
                        flat=True,
                    ).get(pk=object_id)
                    if project:
                        qs = qs.filter(project=project)
                except self.model.DoesNotExist:
                    pass
            kwargs["queryset"] = qs
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class LocationAdmin(
    TagFilterMixin, ExportMixin, ModelAdmin, ProjectBasedPermissionMixin
):
    """Admin interface for Location records with export and project-based permissions."""

    save_on_top = True
    change_form_show_cancel_button = True
    compressed_fields = True
    warn_unsaved_form = True
    list_per_page = 20
    resource_classes = [LocationResource]
    readonly_fields = [
        "id",
        "location",
        "created_at",
        "created_by",
        "modified_at",
        "updated_by",
    ]
    list_display = [
        "identifier",
        "colored_data_source",
        "location_type",
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
            "location_type",
            ChoicesDropdownFilter,
        ),
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

    @display(
        label={"internal": "success", "literature": "info"},
        description="Data Source",
    )
    def colored_data_source(self, obj: Location) -> str:
        """Return the data source value for colour-coded display."""
        return obj.data_source

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Return queryset with related project, campaign, and reference pre-fetched."""
        return (
            super()
            .get_queryset(request)
            .select_related("project", "campaign", "reference")
        )

    fieldsets = (
        (
            "Identification",
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    ("identifier", "data_source"),
                    ("location_type",),
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
                    ("gps_accuracy", "positioning_method"),
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
    """Admin interface for StudyArea records with export and project-based permissions."""

    save_on_top = True
    change_form_show_cancel_button = True
    compressed_fields = True
    warn_unsaved_form = True
    readonly_fields = [
        "id",
        "created_at",
        "created_by",
        "modified_at",
        "updated_by",
    ]
    list_display = [
        "label",
        "project",
        "province",
        "climate_koeppen",
        "ecozone_schultz",
    ]
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
    """Admin interface for Site records with geo support and nested project permissions."""

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
    """Admin interface for Campaign records with export and project-based permissions."""

    save_on_top = True
    change_form_show_cancel_button = True
    compressed_fields = True
    warn_unsaved_form = True
    list_per_page = 20
    readonly_fields = [
        "id",
        "created_at",
        "created_by",
        "modified_at",
        "updated_by",
    ]
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
    def colored_season(self, obj: Campaign) -> str:
        """Return the season value for colour-coded display."""
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
    """Admin interface for Layer records with nested project permissions."""

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


class SampleAdmin(
    TagFilterMixin, ExportMixin, ModelAdmin, HybridProjectPermissionMixin
):
    """Admin interface for Sample records with analysis sub-views and hybrid project permissions."""

    save_on_top = True
    change_form_show_cancel_button = True
    compressed_fields = True
    warn_unsaved_form = True
    show_full_result_count = False
    readonly_fields = [
        "id",
        "created_at",
        "created_by",
        "modified_at",
        "updated_by",
    ]
    search_fields = ["identifier", "location__identifier"]
    autocomplete_fields = [
        "project",
        "location",
        "processor",
        "parent",
        "layer",
        "type",
    ]
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
        ("cosmogenicnuclidedating", "analysis.models.CosmogenicNuclideDating"),
    ]

    def get_urls(self) -> list:
        """Register custom analysis sub-view URLs for each registered analysis model."""
        from importlib import import_module

        def _load(dotted: str) -> type:
            mod, cls = dotted.rsplit(".", 1)
            return getattr(import_module(mod), cls)

        custom_urls = []
        for slug, model_path in self._ANALYSIS_REGISTRY:
            model_class = _load(model_path)
            prefix = f"field_data_sample_{slug}"

            def make_views(m: type) -> tuple:
                def _cl(request: HttpRequest, sample_pk: int) -> HttpResponse:
                    return self._analysis_changelist_view(
                        request,
                        sample_pk,
                        m,
                    )

                def _add(request: HttpRequest, sample_pk: int) -> HttpResponse:
                    return self._analysis_add_view(request, sample_pk, m)

                def _change(
                    request: HttpRequest,
                    sample_pk: int,
                    object_id: str,
                ) -> HttpResponse:
                    return self._analysis_change_view(
                        request,
                        sample_pk,
                        m,
                        object_id,
                    )

                return _cl, _add, _change

            cl_view, add_view, change_view = make_views(model_class)
            custom_urls += [
                path(
                    f"<int:sample_pk>/{slug}/",
                    self.admin_site.admin_view(cl_view),
                    name=prefix,
                ),
                path(
                    f"<int:sample_pk>/{slug}/add/",
                    self.admin_site.admin_view(add_view),
                    name=f"{prefix}_add",
                ),
                path(
                    f"<int:sample_pk>/{slug}/<path:object_id>/change/",
                    self.admin_site.admin_view(change_view),
                    name=f"{prefix}_change",
                ),
            ]
        return custom_urls + super().get_urls()

    def _get_accessible_sample(
        self,
        request: HttpRequest,
        sample_pk: int,
    ) -> None:
        """Return Sample if accessible; raise 404 if missing, 403 if forbidden."""
        get_object_or_404(Sample, pk=sample_pk)
        if not self.get_queryset(request).filter(pk=sample_pk).exists():
            raise PermissionDenied

    def _analysis_changelist_view(
        self,
        request: HttpRequest,
        sample_pk: int,
        model_class: type,
    ) -> HttpResponse:
        """Render an analysis model's changelist filtered for sample_pk."""
        self._get_accessible_sample(request, sample_pk)
        analysis_admin = self.admin_site.get_model_admin(model_class)

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

            pf = urlencode(
                {"_changelist_filters": f"sample__id__exact={sample_pk}"},
            )
            response.context_data["preserved_filters"] = pf
            cl = response.context_data.get("cl")
            if cl is not None:
                cl.preserved_filters = pf

        return response

    # ------------------------------------------------------------------
    # Add-view helpers
    # ------------------------------------------------------------------

    def _analysis_add_view(
        self,
        request: HttpRequest,
        sample_pk: int,
        model_class: type,
    ) -> HttpResponse:
        self._get_accessible_sample(request, sample_pk)
        analysis_admin = self.admin_site.get_model_admin(model_class)
        mutable_get = request.GET.copy()
        mutable_get["sample"] = str(sample_pk)
        request.GET = mutable_get
        response = analysis_admin.add_view(request)
        if hasattr(response, "context_data"):
            from urllib.parse import urlencode

            response.context_data["preserved_filters"] = urlencode(
                {"_changelist_filters": f"sample__id__exact={sample_pk}"},
            )
        return response

    # ------------------------------------------------------------------
    # Change-view helpers
    # ------------------------------------------------------------------

    def _analysis_change_view(
        self,
        request: HttpRequest,
        sample_pk: int,
        model_class: type,
        object_id: str,
    ) -> HttpResponse:
        self._get_accessible_sample(request, sample_pk)
        # Ensure the analysis object actually belongs to the declared sample so
        # a crafted URL like /sample/1/luminescencedating/99/change/ cannot expose
        # a measurement that belongs to an inaccessible sample.
        get_object_or_404(model_class, pk=object_id, sample_id=sample_pk)
        analysis_admin = self.admin_site.get_model_admin(model_class)
        response = analysis_admin.change_view(request, str(object_id))
        if hasattr(response, "context_data"):
            from urllib.parse import urlencode

            response.context_data["preserved_filters"] = urlencode(
                {"_changelist_filters": f"sample__id__exact={sample_pk}"},
            )
        return response


class SampleTypeAdmin(ExportMixin, ModelAdmin):
    """Admin interface for SampleType records."""

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
    """Admin interface for Tag records with project-based permissions."""

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

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: QuerySet,
        search_term: str,
    ) -> tuple:
        """Filter tag search results by content type and project when called from a related field."""
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )
        app_label = request.GET.get("app_label")
        field_name = request.GET.get("field_name")
        model_name = request.GET.get("model_name")
        model_map = {"location": Location, "sample": Sample}
        if (
            app_label == "field_data"
            and field_name == "tags"
            and model_name in model_map
        ):
            model_class = model_map[model_name]
            queryset = queryset.filter(
                content_type=ContentType.objects.get_for_model(model_class),
            )
            match = re.search(
                rf"/{model_name}/(\d+)/change/",
                request.META.get("HTTP_REFERER", ""),
            )
            if match:
                object_pk = int(match.group(1))
                # Validate via the model's own admin queryset (permission-filtered) so a
                # crafted Referer header cannot expose data from inaccessible projects.
                try:
                    model_admin = self.admin_site.get_model_admin(model_class)
                except admin.sites.NotRegistered:
                    model_admin = None
                if model_admin:
                    accessible = model_admin.get_queryset(request).filter(
                        pk=object_pk,
                    )
                    project_id = accessible.values_list(
                        "project",
                        flat=True,
                    ).first()
                    if project_id:
                        queryset = queryset.filter(project=project_id)
        return queryset, may_have_duplicates


class TransectAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    """Admin interface for Transect records with nested project permissions."""

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
