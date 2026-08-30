"""Django admin configuration for field_data models."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from django import forms as django_forms
from django.contrib import messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis import admin
from django.core.exceptions import PermissionDenied
from django.db.models import FileField
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from import_export.admin import ExportMixin, ImportExportMixin
from unfold.admin import (
    GenericTabularInline,
    ModelAdmin,
    StackedInline,
    TabularInline,
)
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
    _project_scoped_queryset,
)

from .models import (
    _SRID_WGS84,
    _UTM_N_SRID_MIN,
    _UTM_S_SRID_MIN,
    Campaign,
    Country,
    ExposureType,
    FieldPhoto,
    Layer,
    Location,
    Province,
    Sample,
    SampleType,
    Site,
    StudyArea,
    Tag,
    Transect,
    _validate_coord_bounds,
)
from .resources import (
    CountryResource,
    ExposureTypeResource,
    LocationResource,
    ProvinceResource,
    SampleTypeResource,
    SiteResource,
)

if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin as DjangoModelAdmin
    from django.db.models import ForeignKey, ManyToManyField, QuerySet
    from django.forms import ModelChoiceField, ModelMultipleChoiceField
    from django.http import HttpResponse

    from prototype.mixins import AuthenticatedHttpRequest
    from prototype.models import Project

    _AdminBase = DjangoModelAdmin[Any]
else:
    _AdminBase = object


def _project_for_field_photo_target(obj: object) -> Project | None:
    """Resolve the owning Project for a FieldPhoto's content_object.

    FieldPhoto attaches via a GenericForeignKey to Location or Layer today
    (see FieldPhoto's own docstring) - Location has a direct project FK,
    Layer reaches it via location.project. Returns None (fail closed) for
    any content_object type this doesn't recognize, rather than guessing.
    """
    if isinstance(obj, Location):
        return obj.project
    if isinstance(obj, Layer):
        # Layer.location is a required (non-nullable) FK - always set.
        return obj.location.project
    return None


class _ProtectedFieldFileProxy:
    """Wraps a bound FieldFile so the admin file widget links to a URL.

    Points at the permission-gated download view instead of the raw (in
    production, unauthenticated) media URL - see FieldPhotoAdmin.download_file.
    """

    def __init__(self, field_file: object, protected_url: str) -> None:
        self._field_file = field_file
        self.url = protected_url

    def __str__(self) -> str:
        return str(self._field_file)


class _ProtectedClearableFileInput(django_forms.ClearableFileInput):
    """ClearableFileInput whose "Currently: <link>" points elsewhere.

    Uses the protected download view instead of the FieldFile's raw .url.
    """

    def format_value(self, value: object) -> object:  # type: ignore[override]
        formatted = super().format_value(value)
        if formatted is None:
            return None
        instance = getattr(formatted, "instance", None)
        if instance is not None and instance.pk:
            protected_url = reverse(
                "admin:field_data_fieldphoto_download", args=[instance.pk]
            )
            return _ProtectedFieldFileProxy(formatted, protected_url)
        return formatted


class FieldPhotoTabularInline(GenericTabularInline):
    """Generic tabular inline for FieldPhoto records attached to any model."""

    model = FieldPhoto
    tab = True
    extra = 0
    fields = [
        "file",
        "caption",
        "taken_at",
    ]
    formfield_overrides = {
        FileField: {"widget": _ProtectedClearableFileInput},
    }


@admin.register(FieldPhoto)
class FieldPhotoAdmin(ModelAdmin):
    """Admin for FieldPhoto - exists to host the protected download route.

    The real editing interface is FieldPhotoTabularInline; this class is
    hidden from the admin index since it's not meant to be browsed directly.
    """

    def has_module_permission(
        self, _request: AuthenticatedHttpRequest
    ) -> bool:
        """Hide from the admin index nav - edited via the inline instead."""
        return False

    def get_urls(self) -> list[object]:
        """Add a project-scoped download route alongside the default admin URLs."""
        custom_urls = [
            path(
                "<int:object_id>/download/",
                self.admin_site.admin_view(self.download_file),
                name="field_data_fieldphoto_download",
            ),
        ]
        return custom_urls + super().get_urls()  # type: ignore[no-any-return]

    def download_file(
        self, request: AuthenticatedHttpRequest, object_id: int
    ) -> FileResponse:
        """Stream a field photo's file to users who can view its owning project.

        In production Django doesn't serve MEDIA_URL at all (see
        prototype/urls.py) - a raw FieldFile.url relies entirely on the
        reverse proxy happening to gate /media/, which nothing enforces.
        Routing through this view instead ties access to the same
        view_project permission used everywhere else in this app.
        """
        photo = get_object_or_404(FieldPhoto, pk=object_id)
        if not photo.file:
            raise Http404
        if not request.user.is_superuser:
            project = _project_for_field_photo_target(photo.content_object)
            if project is None or not request.user.has_perm(
                "prototype.view_project", project
            ):
                raise Http404
        filename = (photo.file.name or "").rsplit("/", 1)[-1]
        return FileResponse(
            photo.file.open("rb"), as_attachment=True, filename=filename
        )


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
                "description": (
                    "Munsell notation: e.g. 7.5YR 4/6 → hue_value=7.5, hue=YR, value=4, chroma=6. "
                    "Step size for all numeric fields: 0.5."
                ),
                "fields": (
                    ("munsell_hue_value", "munsell_hue"),
                    ("munsell_value", "munsell_chroma"),
                ),
            },
        ),
    )


class CountryAdmin(
    ImportExportMixin,
    ModelAdmin,
    admin.GISModelAdmin,  # type: ignore[type-arg]
):
    """Admin interface for Country records."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    resource_classes = [CountryResource]
    list_display = ["name", "iso_code"]
    search_fields = ["name", "iso_code"]
    ordering = ["name"]
    list_filter_sheet = False
    list_filter_submit = True


class ProvinceAdmin(
    ImportExportMixin,
    ModelAdmin,
    admin.GISModelAdmin,  # type: ignore[type-arg]
):
    """Admin interface for Province records."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    resource_classes = [ProvinceResource]
    list_display = ["name", "country"]
    search_fields = ["name", "country__name"]
    ordering = ["name"]
    list_filter = [("country", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True

    def get_queryset(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self, request: AuthenticatedHttpRequest
    ) -> QuerySet[Province]:
        """select_related('country') — list_display renders it per row."""
        return super().get_queryset(request).select_related("country")


class ExposureTypeAdmin(ImportExportMixin, ModelAdmin):
    """Admin interface for ExposureType records."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    resource_classes = [ExposureTypeResource]
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


class BulkTagForm(django_forms.Form):
    """Form used on the intermediate bulk-tag-action page."""

    tags = django_forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        widget=django_forms.CheckboxSelectMultiple,
        required=False,
        label="Tags",
    )

    def __init__(
        self, tag_qs: object, *args: object, **kwargs: object
    ) -> None:
        """Bind the tag queryset to the tags field."""
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.fields["tags"].queryset = tag_qs  # type: ignore[attr-defined]


class BulkTagActionMixin(_AdminBase):
    """Admin mixin that adds add/remove bulk tag actions."""

    actions = ["add_tags_to_selected", "remove_tags_from_selected"]

    def _bulk_write_tags(
        self, queryset: QuerySet[Any], tags: list[Tag], verb: str
    ) -> None:
        """Add/remove *tags* on every object in *queryset* in bulk.

        Writes directly through the "tags" M2M's auto-generated through
        model instead of looping `obj.tags.add(*tags)`/`.remove(*tags)`
        once per selected object — the loop issued one M2M query (or more)
        per object, O(N) round-trips for an N-object admin selection.
        Field names (self_field/tag_field) are derived from the M2M field
        itself so this works for every model that includes this mixin
        (Location/Sample/Site/Layer all define their own "tags" field).
        """
        m2m_field = self.model._meta.get_field("tags")
        through = m2m_field.remote_field.through
        self_field = m2m_field.m2m_field_name()
        tag_field = m2m_field.m2m_reverse_field_name()
        if verb == "add":
            through.objects.bulk_create(
                [
                    through(**{self_field: obj, tag_field: tag})
                    for obj in queryset
                    for tag in tags
                ],
                ignore_conflicts=True,
            )
        else:
            through.objects.filter(
                **{f"{self_field}__in": queryset, f"{tag_field}__in": tags}
            ).delete()

    def _bulk_tag_action(
        self,
        request: AuthenticatedHttpRequest,
        queryset: QuerySet[Any],
        action_name: str,
        verb: str,
    ) -> HttpResponse | None:
        from django.template.response import TemplateResponse

        ct = ContentType.objects.get_for_model(self.model)
        project_ids = queryset.values_list("project", flat=True).distinct()
        tag_qs = Tag.objects.filter(content_type=ct, project__in=project_ids)

        if "_apply_tag_action" in request.POST:
            form = BulkTagForm(tag_qs, request.POST)
            if form.is_valid():
                selected_tags = list(form.cleaned_data["tags"])
                count = queryset.count()
                self._bulk_write_tags(queryset, selected_tags, verb)
                past = "added to" if verb == "add" else "removed from"
                self.message_user(
                    request,
                    f"Tags {past} {count} record(s).",
                    messages.SUCCESS,
                )
                return None
        else:
            form = BulkTagForm(tag_qs)

        return TemplateResponse(
            request,
            "admin/field_data/bulk_tag_action.html",
            {
                **self.admin_site.each_context(request),
                "title": "Add tags" if verb == "add" else "Remove tags",
                "queryset": queryset,
                "action_name": action_name,
                "verb": verb,
                "form": form,
                "action_checkbox_name": ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
                "media": self.media,
            },
        )

    @admin.action(description="Add tags to selected")
    def add_tags_to_selected(
        self,
        request: AuthenticatedHttpRequest,
        queryset: QuerySet[Any],
    ) -> HttpResponse | None:
        """Open an intermediate page to add tags to all selected records."""
        return self._bulk_tag_action(
            request, queryset, "add_tags_to_selected", "add"
        )

    @admin.action(description="Remove tags from selected")
    def remove_tags_from_selected(
        self,
        request: AuthenticatedHttpRequest,
        queryset: QuerySet[Any],
    ) -> HttpResponse | None:
        """Open an intermediate page to remove tags from all selected records."""
        return self._bulk_tag_action(
            request, queryset, "remove_tags_from_selected", "remove"
        )


class TagFilterMixin(_AdminBase):
    """Restrict the tags M2M dropdown to the current model's content type and project."""

    def formfield_for_manytomany(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self,
        db_field: ManyToManyField[Any, Any],
        request: AuthenticatedHttpRequest,
        **kwargs: object,
    ) -> ModelMultipleChoiceField[Any] | None:
        """Filter tag choices to the current model's content type and project."""
        if db_field.name == "tags":
            ct = ContentType.objects.get_for_model(self.model)
            qs = Tag.objects.filter(content_type=ct)
            object_id = (
                request.resolver_match.kwargs.get("object_id")
                if request.resolver_match
                else None
            )
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
    BulkTagActionMixin,
    TagFilterMixin,
    ImportExportMixin,
    ProjectBasedPermissionMixin,
    ModelAdmin,
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
        FieldPhotoTabularInline,
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
        from django_vite.core.asset_loader import DjangoViteAssetLoader

        if not obj.pk or obj.location is None:
            return "Enter easting and northing, then save to see a satellite preview."
        lon = obj.location.x
        lat = obj.location.y
        # generate_vite_asset is the same call django-vite's {% vite_asset %}
        # template tag makes internally; called directly here since this
        # widget is built from a plain string, not a rendered template.
        asset_tags = DjangoViteAssetLoader.instance().generate_vite_asset(
            "src/adminLocationPreview.js"
        )
        html = (
            f'<div class="cgdb-loc-preview" data-lon="{lon}" data-lat="{lat}" '
            'style="width:100%;height:300px;border-radius:4px;margin-top:4px;">'
            f"</div>\n{asset_tags}"
        )
        return mark_safe(html)  # noqa: S308  # nosec B703 B308 — interpolates only floats (lon/lat) via generate_vite_asset's own manifest-driven URLs; no user-controlled strings

    map_preview.short_description = "Map preview (satellite)"  # type: ignore[attr-defined]

    def get_queryset(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self, request: AuthenticatedHttpRequest
    ) -> QuerySet[Location]:
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


class StudyAreaAdmin(
    ExportMixin,
    ProjectBasedPermissionMixin,
    ModelAdmin,
    admin.GISModelAdmin,  # type: ignore[type-arg]
):
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

    def get_queryset(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self, request: AuthenticatedHttpRequest
    ) -> QuerySet[StudyArea]:
        """Return queryset with related project and province pre-fetched.

        Avoids one extra query per FK column per row on the changelist —
        list_display includes both.
        """
        return (
            super().get_queryset(request).select_related("project", "province")
        )

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
    ImportExportMixin,
    NestedProjectPermissionMixin,
    ModelAdmin,
):
    """Admin interface for Site records with nested project permissions.

    Site has no geometry field (label/study_area/tags only) — the GIS admin
    mixin this class used to carry was dead weight left over from an earlier
    iteration of the model.
    """

    change_form_show_cancel_button = True
    list_fullwidth = True
    resource_classes = [SiteResource]
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

    def get_queryset(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self, request: AuthenticatedHttpRequest
    ) -> QuerySet[Site]:
        """Return queryset with related study_area pre-fetched."""
        return super().get_queryset(request).select_related("study_area")

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


class CampaignAdmin(ExportMixin, ProjectBasedPermissionMixin, ModelAdmin):
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

    def get_queryset(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self, request: AuthenticatedHttpRequest
    ) -> QuerySet[Campaign]:
        """Return queryset with related project and destination_country pre-fetched."""
        return (
            super()
            .get_queryset(request)
            .select_related("project", "destination_country")
        )

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


class LayerAdminForm(django_forms.ModelForm):  # type: ignore[type-arg]
    """ModelForm for Layer with help text on Munsell colour fields."""

    class Meta:
        """Metadata for LayerAdminForm."""

        model = Layer
        fields = "__all__"  # noqa: DJ007 — admin form; fieldsets control visibility

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Set Munsell field help texts."""
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.fields[
            "munsell_hue_value"
        ].help_text = "Numeric prefix of the hue page (0–10, step 0.5); e.g. 7.5 for 7.5YR."
        self.fields["munsell_hue"].help_text = "Hue letter code; e.g. YR."
        self.fields[
            "munsell_value"
        ].help_text = "Lightness value (0–10, step 0.5); e.g. 4."
        self.fields[
            "munsell_chroma"
        ].help_text = "Chroma/saturation (0–12, step 0.5); e.g. 6."


class LayerAdmin(ExportMixin, NestedProjectPermissionMixin, ModelAdmin):
    """Admin interface for Layer records with nested project permissions."""

    form = LayerAdminForm
    change_form_show_cancel_button = True
    list_fullwidth = True
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
    readonly_fields = AUDIT_READONLY_FIELDS
    inlines = [FieldPhotoTabularInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "location",
                    ("identifier", "token"),
                    "description",
                    ("depth_top", "depth_bottom"),
                    ("structure", "fine_soil_field"),
                    ("calcite", "secondary_calcite"),
                    "tags",
                    ("created_by", "created_at"),
                    ("updated_by", "modified_at"),
                ),
            },
        ),
        (
            "Munsell Color",
            {
                "description": (
                    "Munsell notation: e.g. 7.5YR 4/6 → hue_value=7.5, hue=YR, value=4, chroma=6. "
                    "Step size for all numeric fields: 0.5."
                ),
                "fields": (
                    ("munsell_hue_value", "munsell_hue"),
                    ("munsell_value", "munsell_chroma"),
                ),
            },
        ),
    )


class SampleAdmin(
    BulkTagActionMixin,
    TagFilterMixin,
    ExportMixin,
    HybridProjectPermissionMixin,
    ModelAdmin,
):
    """Admin interface for Sample records with analysis sub-views and hybrid project permissions."""

    save_on_top = True
    change_form_show_cancel_button = True
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True
    show_full_result_count = False
    readonly_fields = ["id", "depth_mid", *AUDIT_READONLY_FIELDS]
    search_fields = ["identifier", "location__identifier"]
    autocomplete_fields = [
        "project",
        "location",
        "processor",
        "parent",
        "layer",
        "type",
    ]
    list_display = [
        "identifier",
        "project",
        "location",
        "depth_mid",
        "colored_status",
    ]
    inlines = []
    list_filter = [
        ("project", RelatedDropdownFilter),
        ("location__campaign", RelatedDropdownFilter),
        ("location", RelatedDropdownFilter),
        ("status", ChoicesDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True

    @display(
        label={
            "draft": "default",
            "reviewed": "info",
            "accepted": "success",
            "rejected": "danger",
            "archived": "warning",
        },
        description="Status",
    )
    def colored_status(self, obj: Sample) -> str:
        """Return the status value for colour-coded display."""
        return obj.status

    fieldsets = (
        (
            "Sample",
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    ("identifier", "igsn"),
                    "status",
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
                    ("depth_top", "depth_bottom", "depth_mid"),
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

    def get_queryset(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self, request: AuthenticatedHttpRequest
    ) -> QuerySet[Sample]:
        """Return the project-scoped queryset with project/location pre-fetched.

        list_display renders "project" and "location" for every row; without
        select_related each column triggers its own query per row (~2N extra
        queries for N samples on the changelist).
        """
        return (
            super().get_queryset(request).select_related("project", "location")
        )

    def formfield_for_foreignkey(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self,
        db_field: ForeignKey[Any, Any],
        request: AuthenticatedHttpRequest,
        **kwargs: object,
    ) -> ModelChoiceField[Any] | None:
        """Restrict the location dropdown to locations in add_project-permitted projects.

        Narrower than the previous view-level restriction: reassigning a
        Sample's location is effectively adding data under that location's
        project, so it needs add_project, not just view_project — same
        reasoning as HybridProjectPermissionMixin.formfield_for_foreignkey's
        "project" field (prototype/mixins.py), which this pairs with.
        """
        if db_field.name == "location" and not request.user.is_superuser:
            kwargs["queryset"] = _project_scoped_queryset(
                request,
                self.model,  # pyright: ignore[reportArgumentType]  # basedpyright mis-infers self.model through this mixin's unparameterized ModelAdmin base; mypy resolves it correctly
                "location",
                Location,
                "project",
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
                def _cl(
                    request: AuthenticatedHttpRequest, sample_pk: int
                ) -> HttpResponse:
                    return self._analysis_changelist_view(
                        request,
                        sample_pk,
                        m,
                    )

                def _add(
                    request: AuthenticatedHttpRequest, sample_pk: int
                ) -> HttpResponse:
                    return self._analysis_add_view(request, sample_pk, m)

                def _change(
                    request: AuthenticatedHttpRequest,
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
        request: AuthenticatedHttpRequest,
        sample_pk: int,
    ) -> None:
        """Return Sample if accessible; raise 404 if missing, 403 if forbidden."""
        get_object_or_404(Sample, pk=sample_pk)
        if not self.get_queryset(request).filter(pk=sample_pk).exists():
            raise PermissionDenied

    def _analysis_changelist_view(
        self,
        request: AuthenticatedHttpRequest,
        sample_pk: int,
        model_class: type,
    ) -> HttpResponse:
        """Render an analysis model's changelist filtered for sample_pk."""
        self._get_accessible_sample(request, sample_pk)
        analysis_admin: DjangoModelAdmin[Any] = (
            self.admin_site.get_model_admin(model_class)
        )

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

        return response

    # ------------------------------------------------------------------
    # Add-view helpers
    # ------------------------------------------------------------------

    def _analysis_add_view(
        self,
        request: AuthenticatedHttpRequest,
        sample_pk: int,
        model_class: type,
    ) -> HttpResponse:
        self._get_accessible_sample(request, sample_pk)
        analysis_admin: DjangoModelAdmin[Any] = (
            self.admin_site.get_model_admin(model_class)
        )
        mutable_get = request.GET.copy()
        mutable_get["sample"] = str(sample_pk)
        request.GET = mutable_get  # type: ignore[assignment]
        response = analysis_admin.add_view(request)
        if hasattr(response, "context_data"):
            from urllib.parse import urlencode

            response.context_data["preserved_filters"] = urlencode(  # pyright: ignore[reportAttributeAccessIssue]
                {"_changelist_filters": f"sample__id__exact={sample_pk}"},
            )
        return response

    # ------------------------------------------------------------------
    # Change-view helpers
    # ------------------------------------------------------------------

    def _analysis_change_view(
        self,
        request: AuthenticatedHttpRequest,
        sample_pk: int,
        model_class: type,
        object_id: str,
    ) -> HttpResponse:
        self._get_accessible_sample(request, sample_pk)
        # Ensure the analysis object actually belongs to the declared sample so
        # a crafted URL like /sample/1/luminescencedating/99/change/ cannot expose
        # a measurement that belongs to an inaccessible sample.
        get_object_or_404(model_class, pk=object_id, sample_id=sample_pk)
        analysis_admin: DjangoModelAdmin[Any] = (
            self.admin_site.get_model_admin(model_class)
        )
        response = analysis_admin.change_view(request, str(object_id))
        if hasattr(response, "context_data"):
            from urllib.parse import urlencode

            response.context_data["preserved_filters"] = urlencode(  # pyright: ignore[reportAttributeAccessIssue]
                {"_changelist_filters": f"sample__id__exact={sample_pk}"},
            )
        return response


class SampleTypeAdmin(ImportExportMixin, ModelAdmin):
    """Admin interface for SampleType records."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    resource_classes = [SampleTypeResource]
    list_display = [
        "word",
        "label",
    ]
    search_fields = ["word", "label"]
    ordering = ["word"]
    list_filter: list[Any] = []
    list_filter_sheet = False
    list_filter_submit = True


class TagAdmin(ExportMixin, ProjectBasedPermissionMixin, ModelAdmin):
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

    def get_queryset(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self, request: AuthenticatedHttpRequest
    ) -> QuerySet[Tag]:
        """Return queryset with related content_type and project pre-fetched."""
        return (
            super()
            .get_queryset(request)
            .select_related("content_type", "project")
        )

    def get_search_results(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self,
        request: AuthenticatedHttpRequest,
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
        model_map: dict[str, type[Location | Sample]] = {
            "location": Location,
            "sample": Sample,
        }
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


class TransectAdmin(
    ExportMixin,
    NestedProjectPermissionMixin,
    ModelAdmin,
    admin.GISModelAdmin,  # type: ignore[type-arg]
):
    """Admin interface for Transect records with nested project permissions."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    compressed_fields = True
    project_path = "study_area__project"
    readonly_fields = ["id", *AUDIT_READONLY_FIELDS]
    list_display = ["identifier", "study_area", "campaign"]
    search_fields = ["identifier", "study_area__label"]
    list_filter = [
        ("study_area", RelatedDropdownFilter),
        ("campaign", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True
    raw_id_fields = ["study_area", "campaign"]

    def get_queryset(  # type: ignore[override]  # narrowed request param — see AuthenticatedHttpRequest's docstring (prototype/mixins.py) for why this is safe here
        self, request: AuthenticatedHttpRequest
    ) -> QuerySet[Transect]:
        """Return queryset with related study_area and campaign pre-fetched."""
        return (
            super()
            .get_queryset(request)
            .select_related("study_area", "campaign")
        )

    fieldsets = (
        (
            "Transect",
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    ("identifier", "study_area"),
                    ("campaign", "description"),
                    ("created_by", "created_at"),
                    ("updated_by", "modified_at"),
                ),
            },
        ),
        (
            "Geometry",
            {
                "classes": ["tab"],
                "fields": ("multiline",),
            },
        ),
    )


admin.site.register(Country, CountryAdmin)
admin.site.register(Province, ProvinceAdmin)
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
