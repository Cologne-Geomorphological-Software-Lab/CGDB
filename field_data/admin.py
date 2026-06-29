"""Django admin configuration for field_data models."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from django import forms as django_forms
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import path
from import_export.admin import ExportMixin, ImportExportMixin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import display

from prototype.mixins import (
    AUDIT_READONLY_FIELDS,
    HybridProjectPermissionMixin,
    NestedProjectPermissionMixin,
    ProjectBasedPermissionMixin,
    _accessible_projects,
)

from .models import (
    _SRID_WGS84,
    _UTM_N_SRID_MIN,
    _UTM_S_SRID_MIN,
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
    _validate_coord_bounds,
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
    list_fullwidth = True
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
        if db_field.name == "tags":  # type: ignore[attr-defined]
            ct = ContentType.objects.get_for_model(self.model)  # type: ignore[attr-defined]
            qs = Tag.objects.filter(content_type=ct)
            object_id = request.resolver_match.kwargs.get(  # type: ignore[union-attr]
                "object_id"
            )
            if object_id:
                try:
                    project = self.model.objects.values_list(  # type: ignore[attr-defined]
                        "project",
                        flat=True,
                    ).get(pk=object_id)
                    if project:
                        qs = qs.filter(project=project)
                except self.model.DoesNotExist:  # type: ignore[attr-defined]
                    pass
            kwargs["queryset"] = qs
        return super().formfield_for_manytomany(db_field, request, **kwargs)  # type: ignore[no-any-return, misc]


def _srid_choices() -> list[tuple[int, str]]:
    _utm_n_base = _UTM_N_SRID_MIN - 1
    _utm_s_base = _UTM_S_SRID_MIN - 1
    return [
        (_SRID_WGS84, f"EPSG:{_SRID_WGS84} — WGS-84 (decimal degrees)"),
        *[
            (_utm_n_base + z, f"EPSG:{_utm_n_base + z} — UTM Zone {z}N")
            for z in range(1, 61)
        ],
        *[
            (_utm_s_base + z, f"EPSG:{_utm_s_base + z} — UTM Zone {z}S")
            for z in range(1, 61)
        ],
    ]


class LocationAdminForm(django_forms.ModelForm):  # type: ignore[type-arg]
    """ModelForm for Location with a SRID dropdown instead of a raw integer field."""

    srid = django_forms.TypedChoiceField(
        choices=_srid_choices(),
        coerce=int,
        initial=_SRID_WGS84,
        label="CRS (SRID)",
        help_text=(
            "EPSG code — e.g. 4326 (WGS-84 decimal degrees), "
            "32632 (UTM zone 32N), 32633 (UTM zone 33N)."
        ),
    )

    class Meta:
        """Metadata for LocationAdminForm."""

        model = Location
        fields = "__all__"  # noqa: DJ007 — admin form; fieldsets control visibility

    def clean(self) -> dict[str, Any]:
        """Validate coordinate ranges against the selected CRS."""
        cleaned_data: dict[str, Any] = super().clean() or {}
        easting: float | None = cleaned_data.get("easting")
        northing: float | None = cleaned_data.get("northing")
        srid: int = cleaned_data.get("srid", _SRID_WGS84)
        if easting is None or northing is None:
            return cleaned_data
        errors: dict[str, str] = {}
        _validate_coord_bounds(errors, easting, northing, srid)
        if errors:
            raise django_forms.ValidationError(errors)
        return cleaned_data


class LocationAdmin(
    TagFilterMixin, ImportExportMixin, ModelAdmin, ProjectBasedPermissionMixin
):
    """Admin interface for Location records with export and project-based permissions."""

    form = LocationAdminForm

    save_on_top = True
    change_form_show_cancel_button = True
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True
    list_per_page = 20
    resource_classes = [LocationResource]
    readonly_fields = [
        "id",
        "location",
        *AUDIT_READONLY_FIELDS,
        "map_preview",
    ]

    class Media:
        """OL 10 assets for the satellite map preview widget."""

        css = {"all": ["https://cdn.jsdelivr.net/npm/ol@10/ol.css"]}
        js = ["https://cdn.jsdelivr.net/npm/ol@10/dist/ol.js"]

    list_display = [
        "identifier",
        "colored_data_source",
        "colored_location_type",
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

    @display(
        label={
            "sampling_location": "info",
            "camp": "warning",
            "road_access": "warning",
            "infrastructure": "warning",
            "weather_station": "success",
            "survey_point": "success",
            "observation": "success",
            "other": "danger",
        },
        description="Type",
    )
    def colored_location_type(self, obj: Location) -> str:
        """Return the location type display value for colour-coded display."""
        return obj.get_location_type_display() or "—"  # pyright: ignore[reportAttributeAccessIssue]

    def map_preview(self, obj: Location) -> str:
        """Render a satellite preview map that reacts to easting/northing changes."""
        from django.utils.safestring import mark_safe

        if not obj.pk or obj.location is None:
            return "Enter easting and northing, then save to see a satellite preview."
        lon = obj.location.x
        lat = obj.location.y
        map_id = f"loc-map-{obj.pk}"
        html = f"""
<div id="{map_id}" style="width:100%;height:300px;border-radius:4px;margin-top:4px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/proj4js/2.11.0/proj4.js"></script>
<script>
(function() {{
  function utmProj4(srid) {{
    if (srid >= 32601 && srid <= 32660)
      return '+proj=utm +zone=' + (srid - 32600) + ' +datum=WGS84 +units=m +no_defs';
    if (srid >= 32701 && srid <= 32760)
      return '+proj=utm +zone=' + (srid - 32700) + ' +south +datum=WGS84 +units=m +no_defs';
    return null;
  }}
  function toWGS84(e, n, srid) {{
    if (srid === 4326) return [e, n];
    var def = utmProj4(srid);
    return def ? proj4(def, 'WGS84', [e, n]) : null;
  }}
  function initLocMap() {{
    if (typeof ol === 'undefined' || typeof proj4 === 'undefined') {{
      setTimeout(initLocMap, 100); return;
    }}
    var lon = {lon}, lat = {lat};
    var markerSrc = new ol.source.Vector({{
      features: [new ol.Feature({{ geometry: new ol.geom.Point(ol.proj.fromLonLat([lon, lat])) }})]
    }});
    var map = new ol.Map({{
      target: '{map_id}',
      layers: [
        new ol.layer.Tile({{ source: new ol.source.XYZ({{
          url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
          maxZoom: 17, attributions: 'Tiles &copy; Esri'
        }}) }}),
        new ol.layer.Vector({{
          source: markerSrc,
          style: new ol.style.Style({{ image: new ol.style.Circle({{
            radius: 8, fill: new ol.style.Fill({{ color: '#3b82f6' }}),
            stroke: new ol.style.Stroke({{ color: '#1d4ed8', width: 2 }})
          }}) }})
        }}),
      ],
      view: new ol.View({{ center: ol.proj.fromLonLat([lon, lat]), zoom: 14 }}),
      controls: [new ol.control.ScaleLine()],
    }});
    function updateMarker() {{
      var e = parseFloat(document.getElementById('id_easting')?.value);
      var n = parseFloat(document.getElementById('id_northing')?.value);
      var srid = parseInt(document.getElementById('id_srid')?.value) || 4326;
      if (!isNaN(e) && !isNaN(n)) {{
        var wgs84 = toWGS84(e, n, srid);
        if (wgs84) {{
          var coord = ol.proj.fromLonLat(wgs84);
          markerSrc.getFeatures()[0].getGeometry().setCoordinates(coord);
          map.getView().setCenter(coord);
        }}
      }}
    }}
    ['id_easting', 'id_northing', 'id_srid'].forEach(function(id) {{
      var el = document.getElementById(id);
      if (el) el.addEventListener('change', updateMarker);
    }});
  }}
  initLocMap();
}})();
</script>"""
        return mark_safe(html)  # noqa: S308  # nosec B703 B308 — interpolates only floats (lon/lat) and integer PK; no user-controlled strings

    map_preview.short_description = "Map preview (satellite)"  # type: ignore[attr-defined]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Location]:
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
                    ("location_type", "exposure_type"),
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
                    "map_preview",
                ),
            },
        ),
        (
            "Field Setting",
            {
                "classes": ["tab"],
                "fields": (
                    ("study_site", "transect"),
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
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True
    readonly_fields = ["id", *AUDIT_READONLY_FIELDS]
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
    admin.options.GeoModelAdminMixin,  # pyright: ignore[reportAttributeAccessIssue]
    NestedProjectPermissionMixin,
):
    """Admin interface for Site records with geo support and nested project permissions."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    project_path = "study_area__project"  # type: ignore[assignment]
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
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True
    list_per_page = 20
    readonly_fields = ["id", *AUDIT_READONLY_FIELDS]
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
        return obj.season or ""

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
    list_fullwidth = True
    project_path = "location__project"  # type: ignore[assignment]
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
    readonly_fields = AUDIT_READONLY_FIELDS


class SampleAdmin(
    TagFilterMixin, ExportMixin, ModelAdmin, HybridProjectPermissionMixin
):
    """Admin interface for Sample records with analysis sub-views and hybrid project permissions."""

    save_on_top = True
    change_form_show_cancel_button = True
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True
    show_full_result_count = False
    readonly_fields = ["id", *AUDIT_READONLY_FIELDS]
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
    inlines: list[Any] = []
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

    def formfield_for_foreignkey(
        self,
        db_field: object,
        request: HttpRequest,
        **kwargs: object,
    ) -> Field | None:
        """Restrict the location dropdown to locations in accessible projects."""
        if db_field.name == "location":  # type: ignore[attr-defined]
            kwargs["queryset"] = Location.objects.filter(
                project__in=_accessible_projects(request.user)
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)  # type: ignore[no-any-return]

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

    def get_urls(self) -> list[Any]:
        """Register custom analysis sub-view URLs for each registered analysis model."""
        from importlib import import_module

        def _load(dotted: str) -> type[Any]:
            mod, cls = dotted.rsplit(".", 1)
            return getattr(import_module(mod), cls)  # type: ignore[no-any-return]

        custom_urls = []
        for slug, model_path in self._ANALYSIS_REGISTRY:
            model_class = _load(model_path)
            prefix = f"field_data_sample_{slug}"

            def make_views(m: type[Any]) -> tuple[Any, ...]:
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
        return custom_urls + super().get_urls()  # type: ignore[no-any-return]

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
        request.GET = mutable_get  # type: ignore[assignment]

        response = analysis_admin.changelist_view(request)

        # get_preserved_filters() checks current_url == changelist_url — fails for
        # our custom sub-view URLs. Patch both the context variable AND cl.preserved_filters
        # (used by the empty-state template via {% include ... with preserved_filters=cl.preserved_filters %}).
        if hasattr(response, "context_data"):
            from urllib.parse import urlencode

            pf = urlencode(
                {"_changelist_filters": f"sample__id__exact={sample_pk}"},
            )
            response.context_data["preserved_filters"] = pf  # pyright: ignore[reportAttributeAccessIssue]
            cl = response.context_data.get("cl")  # pyright: ignore[reportAttributeAccessIssue]
            if cl is not None:
                cl.preserved_filters = pf

        return response  # type: ignore[no-any-return]

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
        request.GET = mutable_get  # type: ignore[assignment]
        response = analysis_admin.add_view(request)
        if hasattr(response, "context_data"):
            from urllib.parse import urlencode

            response.context_data["preserved_filters"] = urlencode(  # pyright: ignore[reportAttributeAccessIssue]
                {"_changelist_filters": f"sample__id__exact={sample_pk}"},
            )
        return response  # type: ignore[no-any-return]

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

            response.context_data["preserved_filters"] = urlencode(  # pyright: ignore[reportAttributeAccessIssue]
                {"_changelist_filters": f"sample__id__exact={sample_pk}"},
            )
        return response  # type: ignore[no-any-return]


class SampleTypeAdmin(ExportMixin, ModelAdmin):
    """Admin interface for SampleType records."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = [
        "word",
        "label",
    ]
    search_fields = ["word", "label"]
    ordering = ["word"]
    list_filter: list[Any] = []
    list_filter_sheet = False
    list_filter_submit = True


class TagAdmin(ExportMixin, ModelAdmin, ProjectBasedPermissionMixin):
    """Admin interface for Tag records with project-based permissions."""

    change_form_show_cancel_button = True
    list_fullwidth = True
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
        queryset: QuerySet[Any],
        search_term: str,
    ) -> tuple[QuerySet[Any], bool]:
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
                except admin.sites.NotRegistered:  # type: ignore[attr-defined]
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
    list_fullwidth = True
    project_path = "study_area__project"  # type: ignore[assignment]
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
