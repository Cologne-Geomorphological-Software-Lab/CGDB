"""Django admin registrations for the analysis app."""

from __future__ import annotations

import base64
import io

import matplotlib as mpl
import matplotlib.pyplot as plt
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ExportMixin, ImportExportMixin
from PIL import Image
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RelatedDropdownFilter
from unfold.decorators import display

from prototype.mixins import (
    CreatedUpdatedModelAdminMixin,
    NestedProjectPermissionMixin,
)

from .models import (
    Algorithm,
    CosmogenicNuclideDating,
    Counting,
    GenericMeasurement,
    GrainSize,
    LuminescenceDating,
    MeasurementSeries,
    MicroXRFElementMap,
    MicroXRFMeasurement,
    Parameter,
    Pollen,
    PollenCount,
    RadiocarbonDating,
    RawMeasurement,
    RawProcessing,
)

mpl.use("Agg")


class SampleContextMixin:
    """Keeps all measurement forms under the Sample URL hierarchy.

    - add_view / change_view: redirect to the sample-scoped URL when accessed
      via the standard /admin/analysis/... paths.
    - get_changeform_initial_data: pre-fills the sample FK.
    - response_add / response_change: after saving, return to the Sample form.
    """

    def _is_sample_scoped(self, request: HttpRequest) -> bool:
        url_name = (
            getattr(getattr(request, "resolver_match", None), "url_name", "")
            or ""
        )
        return url_name.startswith("field_data_sample_")

    def _sample_pk_from_add_request(self, request: HttpRequest) -> str | None:
        from field_data.utils import extract_sample_pk_from_get

        return extract_sample_pk_from_get(request.GET)

    def changelist_view(
        self,
        request: HttpRequest,
        extra_context: dict | None = None,
    ) -> HttpResponse:
        """Redirect to the sample-scoped changelist when a sample filter is active."""
        if not self._is_sample_scoped(request):
            sample_pk = request.GET.get("sample__id__exact", "")
            if sample_pk and sample_pk.isdigit():
                model_name = self.model._meta.model_name
                try:
                    url = reverse(
                        f"admin:field_data_sample_{model_name}",
                        args=[sample_pk],
                    )
                    return redirect(url)
                except NoReverseMatch:
                    pass
        return super().changelist_view(request, extra_context)

    def add_view(
        self,
        request: HttpRequest,
        form_url: str = "",
        extra_context: dict | None = None,
    ) -> HttpResponse:
        """Redirect to the sample-scoped add URL when accessed outside sample context."""
        if request.method == "GET" and not self._is_sample_scoped(request):
            sample_pk = self._sample_pk_from_add_request(request)
            if sample_pk:
                model_name = self.model._meta.model_name
                try:
                    url = reverse(
                        f"admin:field_data_sample_{model_name}_add",
                        args=[sample_pk],
                    )
                    return redirect(url)
                except NoReverseMatch:
                    pass
        return super().add_view(request, form_url, extra_context)

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict | None = None,
    ) -> HttpResponse:
        """Redirect to the sample-scoped change URL when accessed outside sample context."""
        if request.method == "GET" and not self._is_sample_scoped(request):
            obj = self.get_object(request, object_id)
            if obj and obj.sample_id:
                model_name = self.model._meta.model_name
                try:
                    url = reverse(
                        f"admin:field_data_sample_{model_name}_change",
                        args=[obj.sample_id, object_id],
                    )
                    return redirect(url)
                except NoReverseMatch:
                    pass
        return super().change_view(request, object_id, form_url, extra_context)

    def get_changeform_initial_data(self, request: HttpRequest) -> dict:
        """Pre-fill the sample FK from changelist filter parameters."""
        initial = super().get_changeform_initial_data(request)
        if "sample" not in initial:
            from urllib.parse import parse_qs

            cl_filters = request.GET.get("_changelist_filters", "")
            if cl_filters:
                params = parse_qs(cl_filters)
                pk_list = params.get("sample__id__exact", [])
                if pk_list:
                    initial["sample"] = pk_list[0]
        return initial

    def _redirect_to_sample(
        self,
        request: HttpRequest,
        obj: object,
    ) -> HttpResponse | None:
        if "_save" in request.POST and getattr(obj, "sample_id", None):
            return redirect(
                reverse(
                    "admin:field_data_sample_change",
                    args=[obj.sample_id],
                ),
            )
        return None

    def response_add(
        self,
        request: HttpRequest,
        obj: object,
        post_url_continue: str | None = None,
    ) -> HttpResponse:
        """Return to the parent Sample form after a successful add."""
        r = self._redirect_to_sample(request, obj)
        return r or super().response_add(request, obj, post_url_continue)

    def response_change(
        self,
        request: HttpRequest,
        obj: object,
    ) -> HttpResponse:
        """Return to the parent Sample form after a successful change."""
        r = self._redirect_to_sample(request, obj)
        return r or super().response_change(request, obj)


# ======================
# RAW DATA ADMIN
# ======================


class AlgorithmAdmin(ExportMixin, ModelAdmin):
    """Admin for the Algorithm model."""

    change_form_show_cancel_button = True
    list_display = ["name", "version", "programming_language"]
    search_fields = ["name", "version"]
    ordering = ["name", "version"]


class RawMeasurementAdmin(
    ExportMixin,
    ModelAdmin,
    NestedProjectPermissionMixin,
):
    """Admin for the RawMeasurement model."""

    change_form_show_cancel_button = True
    warn_unsaved_form = True
    project_path = "sample__location__project"
    list_display = [
        "device",
        "accessories",
        "researcher",
        "file",
        "description",
    ]
    ordering = ["sample__location__project", "sample__location", "sample"]

    search_fields = ["description", "sample__identifier"]
    raw_id_fields = ["device", "accessories", "researcher"]
    list_filter_sheet = False
    list_filter_submit = True
    filter_horizontal = ["sample"]
    list_filter = [
        (
            "sample__location__project",
            RelatedDropdownFilter,
        ),
        (
            "device",
            RelatedDropdownFilter,
        ),
        (
            "accessories",
            RelatedDropdownFilter,
        ),
        (
            "researcher",
            RelatedDropdownFilter,
        ),
    ]


class RawProcessingAdmin(
    ExportMixin,
    ModelAdmin,
    NestedProjectPermissionMixin,
):
    """Admin for the RawProcessing model."""

    change_form_show_cancel_button = True
    warn_unsaved_form = True
    project_path = "raw_measurement__project"
    list_display = [
        "raw_measurement",
    ]


# ======================
# PALEOBOTANY ADMIN
# ======================


class PollenCountInline(TabularInline):
    """Inline for PollenCount entries within a Counting change form."""

    model = PollenCount
    extra = 0


class CountingAdmin(
    SampleContextMixin,
    ExportMixin,
    ModelAdmin,
    NestedProjectPermissionMixin,
):
    """Admin for the Counting model with inline pollen counts."""

    change_form_show_cancel_button = True
    warn_unsaved_form = True
    project_path = "sample__location__project"
    inlines = [PollenCountInline]
    list_display = ["type"]
    list_fullwidth = True
    raw_id_fields = ["sample"]


class PollenAdmin(ExportMixin, ModelAdmin):
    """Admin for the Pollen model."""

    change_form_show_cancel_button = True
    list_display = ["name", "token", "name_en"]
    search_fields = ["name", "token", "name_en"]
    ordering = ["name"]


# ======================
# GEOCHRONOLOGY ADMIN
# ======================


class LuminescenceDatingAdmin(
    SampleContextMixin,
    ImportExportMixin,
    CreatedUpdatedModelAdminMixin,
    NestedProjectPermissionMixin,
    ModelAdmin,
):
    """Admin for LuminescenceDating with tabbed fieldsets and color-coded display columns."""

    project_path = "sample__location__project"
    save_on_top = True
    change_form_show_cancel_button = True
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True
    list_horizontal_scrollbar_top = True
    list_disable_select_all = False

    list_display = [
        "laboratory_id",
        "colored_dating_approach",
        "colored_mineral",
        "age",
        "total_dose_rate",
        "paleodose",
    ]

    raw_id_fields = ["sample", "raw_data"]

    @display(description="Luminescence age [ka]")
    def age(self, obj: LuminescenceDating) -> str:
        """Return formatted age with error, or an em-dash if unavailable."""
        if obj.luminescence_age:
            return (
                f"{round(obj.luminescence_age, 2)} ± {round(obj.age_error, 2)}"
            )
        return "—"

    @display(description="Dose rate [Gy/ka]")
    def total_dose_rate(self, obj: LuminescenceDating) -> str:
        """Return formatted dose rate with error, or an em-dash if unavailable."""
        if obj.dose_rate:
            return (
                f"{round(obj.dose_rate, 2)} ± {round(obj.dose_rate_error, 2)}"
            )
        return "—"

    @display(description="Paleodose [Gy]")
    def paleodose(self, obj: LuminescenceDating) -> str:
        """Return formatted palaeodose with error, or an em-dash if unavailable."""
        if obj.palaeodose_value:
            return f"{round(obj.palaeodose_value, 2)} ± {round(obj.palaeodose_error, 2)}"
        return "—"

    @display(
        label={
            "Quartz": "success",
            "Feldspar": "info",
            "Polymineral": "warning",
            "Other": "default",
        },
        description="Mineral",
    )
    def colored_mineral(self, obj: LuminescenceDating) -> str:
        """Return the mineral type for color-coded label rendering."""
        return obj.mineral

    @display(
        label={
            "Burial dating": "info",
            "Exposure dating": "success",
            "Other": "warning",
        },
        description="Approach",
    )
    def colored_dating_approach(self, obj: LuminescenceDating) -> str:
        """Return the dating approach for color-coded label rendering."""
        return obj.dating_approach

    fieldsets = (
        (
            "Identification",
            {
                "classes": ["tab"],
                "fields": (
                    ("sample", "raw_data"),
                    ("laboratory_id", "sample_id_cll"),
                    ("mineral", "dating_approach"),
                    ("signal", "protocol"),
                ),
            },
        ),
        (
            "Results",
            {
                "classes": ["tab"],
                "fields": (
                    ("luminescence_age", "age_error"),
                    ("palaeodose_value", "palaeodose_error"),
                    ("dose_rate", "dose_rate_error"),
                    "age_model",
                ),
            },
        ),
        (
            "Palaeodose Details",
            {
                "classes": ["tab"],
                "fields": (
                    ("grain_size_min", "grain_size_max"),
                    ("aliquot_size", "aliquot_number_used_for_palaeodose"),
                    ("od_percent", "od_percent_error"),
                    ("od_gy", "od_gy_error"),
                    ("beta_source_calibration", "fading_correction"),
                    (
                        "instrumental_beta_source_error",
                        "uncertainty_beta_source_calibration",
                    ),
                    ("g_value", "g_value_error"),
                    "Lnat_Lsat_ratio",
                ),
            },
        ),
        (
            "Dosimetry",
            {
                "classes": ["tab"],
                "fields": (
                    (
                        "dose_rate_measurement_technique",
                        "dose_rate_calculation_software",
                    ),
                    ("u_ppm", "u_ppm_error"),
                    ("th_ppm", "th_ppm_error"),
                    ("k_percent", "k_percent_error"),
                    (
                        "water_content_for_dating",
                        "water_content_for_dating_error",
                    ),
                    ("a_value", "a_value_error"),
                    ("alpha_dose_rate", "alpha_dose_rate_error"),
                    ("beta_dose_rate", "beta_dose_rate_error"),
                    ("gamma_dose_rate", "gamma_dose_rate_error"),
                    ("cosmic_dose_rate", "cosmic_dose_rate_error"),
                ),
            },
        ),
        (
            "Publication",
            {
                "classes": ["tab"],
                "fields": (
                    ("published", "year_of_publication"),
                    "thesis",
                    "comments",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Return queryset with sample location and project pre-fetched."""
        return (
            super()
            .get_queryset(request)
            .select_related("sample__location__project")
        )


class RadiocarbonDatingAdmin(
    SampleContextMixin,
    ImportExportMixin,
    ModelAdmin,
    NestedProjectPermissionMixin,
):
    """Admin for the RadiocarbonDating model."""

    change_form_show_cancel_button = True
    project_path = "sample__location__project"
    raw_id_fields = ["sample"]
    list_fullwidth = True
    list_display = ["lab_id", "lab", "age"]
    ordering = ["-id"]


class CosmogenicNuclideDatingAdmin(
    SampleContextMixin,
    ExportMixin,
    ModelAdmin,
    NestedProjectPermissionMixin,
):
    """Admin for CosmogenicNuclideDating with tabbed fieldsets and color-coded columns."""

    change_form_show_cancel_button = True
    warn_unsaved_form = True
    compressed_fields = True
    project_path = "sample__location__project"
    list_fullwidth = True
    list_display = [
        "lab_id",
        "colored_nuclide",
        "colored_approach",
        "colored_exposure_age",
    ]
    search_fields = ["lab_id", "sample__identifier"]
    ordering = ["-id"]

    autocomplete_fields = ["sample", "raw_data"]

    fieldsets = (
        (
            "Identification",
            {
                "classes": ["tab"],
                "fields": (
                    ("sample", "raw_data"),
                    ("lab_id", "nuclide", "mineral"),
                    "dating_approach",
                ),
            },
        ),
        (
            "Concentration & Standards",
            {
                "classes": ["tab"],
                "fields": (
                    ("nuclide_concentration", "nuclide_concentration_error"),
                    ("ams_standard",),
                    (
                        "normalized_concentration",
                        "normalized_concentration_error",
                    ),
                ),
            },
        ),
        (
            "Results",
            {
                "classes": ["tab"],
                "fields": (
                    (
                        "exposure_age",
                        "exposure_age_error_internal",
                        "exposure_age_error_external",
                    ),
                    ("burial_age", "burial_age_error"),
                    ("denudation_rate", "denudation_rate_error"),
                ),
            },
        ),
        (
            "Production & Shielding",
            {
                "classes": ["tab"],
                "fields": (
                    ("scaling_method", "calculation_software"),
                    ("production_rate", "production_rate_error"),
                    ("spallation_production_rate", "muon_production_rate"),
                    (
                        "topographic_shielding",
                        "self_shielding",
                        "snow_shielding",
                    ),
                    ("combined_shielding",),
                    ("erosion_rate_assumed", "inheritance"),
                ),
            },
        ),
        (
            "Error Budget",
            {
                "classes": ["tab"],
                "fields": (
                    (
                        "error_ams",
                        "error_muon",
                        "error_production_rate",
                        "error_total",
                    ),
                ),
            },
        ),
        (
            "Publication",
            {
                "classes": ["tab"],
                "fields": (
                    ("published", "year_of_publication", "thesis"),
                    "comments",
                ),
            },
        ),
    )

    @display(
        label={
            "10Be": "info",
            "26Al": "warning",
            "36Cl": "success",
            "3He": "danger",
            "21Ne": "danger",
            "14C": "danger",
        },
        description="Nuclide",
    )
    def colored_nuclide(self, obj: CosmogenicNuclideDating) -> str:
        """Return the nuclide symbol for color-coded label rendering."""
        return obj.nuclide

    @display(
        label={
            "exposure": "success",
            "burial": "warning",
            "denudation": "info",
        },
        description="Approach",
    )
    def colored_approach(self, obj: CosmogenicNuclideDating) -> str:
        """Return the dating approach for color-coded label rendering."""
        return obj.dating_approach

    @display(description="Exposure age [ka]")
    def colored_exposure_age(self, obj: CosmogenicNuclideDating) -> str:
        """Return formatted exposure age with external error, or an em-dash if absent."""
        if obj.exposure_age is None:
            return "—"
        err = (
            f" ± {obj.exposure_age_error_external}"
            if obj.exposure_age_error_external
            else ""
        )
        return f"{obj.exposure_age}{err}"


admin.site.register(CosmogenicNuclideDating, CosmogenicNuclideDatingAdmin)


# ======================
# SEDIMENTOLOGY ADMIN
# ======================


class GenericMeasurementResource(resources.ModelResource):
    """Import/export resource for GenericMeasurement."""

    class Meta:
        """Resource metadata for GenericMeasurement."""

        model = GenericMeasurement

        skip_diff = True
        import_id_fields = ("sample",)


class GeochemistryParameterResource(resources.ModelResource):
    """Import/export resource for Parameter."""

    class Meta:
        """Resource metadata for Parameter."""

        model = Parameter


class GrainSizeImportForm(forms.ModelForm):
    """ModelForm for GrainSize that accepts an optional .av file upload."""

    file = forms.FileField(required=False)

    def clean_file(self) -> object:
        """Validate the uploaded file is a non-empty .av file within the size limit."""
        file = self.cleaned_data.get("file")

        if not file:
            return file

        if not file.name.lower().endswith(".$av"):
            raise ValidationError(
                _("Invalid file type. Only .$av files are allowed."),
            )

        max_size_mb = 10
        if file.size > max_size_mb * 1024 * 1024:
            raise ValidationError(
                _(
                    "File size (%(size).1fMB) exceeds maximum allowed size of %(max)sMB.",
                )
                % {"size": file.size / (1024 * 1024), "max": max_size_mb},
            )

        try:
            file.seek(0)
            first_chunk = file.read(1024)
            file.seek(0)

            if len(first_chunk) == 0:
                raise ValidationError(_("File is empty or corrupted."))
        except Exception as e:
            raise ValidationError(_("Unable to read file: %s") % e) from None

        return file

    class Meta:
        """Form metadata for GrainSizeImportForm."""

        model = GrainSize
        fields = [
            "sample",
            "raw_data",
            "sample_weight",
            "sample_concentration",
            "method",
            "classes",
            "measured_data",
            "clay",
            "fine_silt",
            "medium_silt",
            "coarse_silt",
            "fine_sand",
            "medium_sand",
            "coarse_sand",
            "gravel",
            "mean",
            "mode",
            "median",
            "std",
            "skew",
            "kurtosis",
            "fwmean",
            "fwmedian",
            "fwsd",
            "fwskew",
            "fwkurt",
        ]


_SAMPLE_CONC_MIN = (
    6  # Sympatec Helios optimal range: 6–20 % (volume concentration)
)
_SAMPLE_CONC_MAX = 20


class GrainSizeAdmin(
    SampleContextMixin,
    ExportMixin,
    ModelAdmin,
    NestedProjectPermissionMixin,
):
    """Admin for GrainSize with file import, Wentworth fraction display, and a plot tab."""

    change_form_show_cancel_button = True
    warn_unsaved_form = True
    compressed_fields = True
    project_path = "sample__location__project"
    form = GrainSizeImportForm

    list_fullwidth = True
    list_display = ["colored_method", "colored_sample_concentration"]
    autocomplete_fields = ["sample", "raw_data"]

    readonly_fields = [
        "source",
        "classes_summary",
        "measured_data_summary",
        "colored_sample_concentration",
        "clay",
        "fine_silt",
        "medium_silt",
        "coarse_silt",
        "fine_sand",
        "medium_sand",
        "coarse_sand",
        "gravel",
        "plot",
    ]

    _STAT_FIELDS = [
        "mean",
        "mode",
        "median",
        "std",
        "skew",
        "kurtosis",
        "fwmean",
        "fwmedian",
        "fwsd",
        "fwskew",
        "fwkurt",
    ]

    fieldsets = (
        (
            "Identification",
            {
                "classes": ["tab"],
                "fields": (
                    ("sample", "raw_data"),
                    ("method", "sample_weight"),
                    "source",
                ),
            },
        ),
        (
            "Import",
            {
                "classes": ["tab"],
                "fields": (
                    "file",
                    "classes_summary",
                    "measured_data_summary",
                    "colored_sample_concentration",
                ),
            },
        ),
        (
            "Fractions",
            {
                "classes": ["tab"],
                "fields": (
                    ("clay", "fine_silt", "medium_silt", "coarse_silt"),
                    ("fine_sand", "medium_sand", "coarse_sand", "gravel"),
                ),
            },
        ),
        (
            "Statistics — Standard",
            {
                "classes": ["tab"],
                "fields": (
                    ("mean", "median", "mode"),
                    ("std", "skew", "kurtosis"),
                ),
            },
        ),
        (
            "Statistics — Folk & Ward",
            {
                "classes": ["tab"],
                "fields": (
                    ("fwmean", "fwmedian"),
                    ("fwsd", "fwskew", "fwkurt"),
                ),
            },
        ),
        (
            "Plot",
            {
                "classes": ["tab"],
                "fields": ("plot",),
            },
        ),
    )

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: GrainSize | None = None,
    ) -> list:
        """Make statistics fields read-only when grain size was imported from a file."""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.source == "file":
            readonly += [f for f in self._STAT_FIELDS if f not in readonly]
        return readonly

    @display(
        label={"L": "success", "C": "info", "S": "warning"},
        description="Method",
    )
    def colored_method(self, obj: GrainSize) -> str:
        """Return the measurement method for color-coded label rendering."""
        return obj.method

    @display(description="Sample concentration [%]")
    def colored_sample_concentration(self, obj: GrainSize) -> str:
        """Return a colour-highlighted HTML span for the sample concentration value."""
        if obj.sample_concentration is None:
            return "N/A"
        color = (
            "success"
            if _SAMPLE_CONC_MIN <= obj.sample_concentration <= _SAMPLE_CONC_MAX
            else "danger"
        )
        color = (
            color
            if color in {"success", "danger", "warning", "info"}
            else "danger"
        )
        rounded = round(obj.sample_concentration, 1)
        return mark_safe(  # noqa: S308 — color is whitelist-validated, rounded is float
            f'<span class="text-{color}-600 dark:text-{color}-400 font-semibold">{rounded} %</span>',
        )

    @admin.display(description="Classes")
    def classes_summary(self, obj: GrainSize) -> str:
        """Return a summary of the grain-size class boundaries."""
        if not obj.classes:
            return "—"
        n = len(obj.classes)
        mn = min(obj.classes)
        mx = max(obj.classes)
        return f"{n} classes, {mn}–{mx} µm"

    @admin.display(description="Measured data")
    def measured_data_summary(self, obj: GrainSize) -> str:
        """Return a summary of the measured data points and their total."""
        if not obj.measured_data:
            return "—"
        n = len(obj.measured_data)
        total = sum(obj.measured_data)
        return f"{n} data points, sum = {round(total, 1)}"

    def save_model(
        self,
        request: HttpRequest,
        obj: GrainSize,
        form: ModelForm,
        change: bool,
    ) -> None:
        """Parse and import an uploaded .av file before delegating to super."""
        file = form.cleaned_data.get("file")
        if file:
            self.process_file(file, obj)
            obj.source = "file"
            self.message_user(
                request,
                "File uploaded and processed successfully.",
                messages.SUCCESS,
            )
        super().save_model(request, obj, form, change)

    def process_file(self, file: object, obj: GrainSize) -> None:
        """Save the uploaded file to temp storage, parse it, and populate obj fields."""
        file_path = default_storage.save(
            f"tmp/{file.name}",
            ContentFile(file.read()),
        )
        tmp_file = default_storage.path(file_path)

        grain_size_instance = GrainSize.from_file(
            tmp_file,
            obj.sample,
            obj.method,
        )

        obj.classes = grain_size_instance.classes
        obj.measured_data = grain_size_instance.measured_data
        obj.mean = grain_size_instance.mean
        obj.mode = grain_size_instance.mode
        obj.median = grain_size_instance.median
        obj.std = grain_size_instance.std
        obj.skew = grain_size_instance.skew
        obj.kurtosis = grain_size_instance.kurtosis
        obj.fwmean = grain_size_instance.fwmean
        obj.fwmedian = grain_size_instance.fwmedian
        obj.fwsd = grain_size_instance.fwsd
        obj.fwskew = grain_size_instance.fwskew
        obj.fwkurt = grain_size_instance.fwkurt
        obj.sample_concentration = grain_size_instance.sample_concentration
        default_storage.delete(file_path)

    def plot(self, obj: GrainSize) -> str:
        """Render a log-scale grain size distribution chart as an inline base64 PNG."""
        if not obj.measured_data or not obj.classes:
            return "No data available for plotting."
        fig, ax = plt.subplots(figsize=(30, 10))
        ax.plot(obj.classes, obj.measured_data, marker="")
        ax.set_xscale("log")
        ax.set_xlim(0.04, 2000)
        ax.set_xlabel("Grain Size (μm)", fontsize=21)
        ax.set_ylabel("GSD (%)", fontsize=21)
        ax.tick_params(axis="both", which="major", labelsize=12)
        for x in [0.2, 0.63, 2, 6.3, 20, 63, 200, 630]:
            ax.axvline(x=x, color="black", linestyle="--", linewidth=0.5)
            ax.text(
                x=x,
                y=-0.1,
                s=str(x),
                fontsize=21,
                verticalalignment="top",
                horizontalalignment="center",
                transform=ax.get_xaxis_transform(),
            )
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return mark_safe(  # noqa: S308 — base64-encoded matplotlib PNG, no user input
            f'<img src="data:image/png;base64,{image_base64}" />',
        )

    plot.short_description = "Grain size distribution"


class GenericMeasurementAdmin(
    SampleContextMixin,
    ExportMixin,
    ModelAdmin,
    NestedProjectPermissionMixin,
):
    """Admin for GenericMeasurement with import/export and value-with-error display."""

    change_form_show_cancel_button = True
    warn_unsaved_form = True
    compressed_fields = True
    project_path = "sample__location__project"
    resource_classes = [GenericMeasurementResource]

    list_display = ["parameter__token", "method", "value_with_error"]
    list_fullwidth = True
    autocomplete_fields = ["sample", "parameter", "method"]
    raw_id_fields = ["raw_data", "MeasurementSeries"]

    fieldsets = (
        (
            "Identification",
            {
                "classes": ["tab"],
                "fields": (
                    ("sample", "method"),
                    ("parameter", "sample_weight"),
                    ("raw_data", "MeasurementSeries"),
                ),
            },
        ),
        (
            "Result",
            {
                "classes": ["tab"],
                "fields": (("value", "error"),),
            },
        ),
    )

    @admin.display(description="Value")
    def value_with_error(self, obj: GenericMeasurement) -> str:
        """Return the measured value formatted with its error, or an em-dash if absent."""
        if obj.value is None:
            return "—"
        if obj.error:
            return f"{round(obj.value, 4)} ± {round(obj.error, 4)}"
        return str(round(obj.value, 4))

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Return queryset with method and parameter pre-fetched."""
        return (
            super().get_queryset(request).select_related("method", "parameter")
        )


class ParameterAdmin(ExportMixin, ModelAdmin):
    """Admin for the Parameter model."""

    change_form_show_cancel_button = True
    list_display = ["token", "id", "unit"]
    search_fields = ["token"]
    ordering = ["token"]
    resource_classes = [GeochemistryParameterResource]


class MicroXRFElementInline(admin.TabularInline):
    """Inline for MicroXRFElementMap entries with thumbnail preview."""

    model = MicroXRFElementMap
    hide_title = True
    readonly_fields = ["preview"]
    fields = ["element", "raster_file", "preview"]
    extra = 0

    def preview(self, obj: MicroXRFElementMap) -> str:
        """Render a 120 px thumbnail of the element map raster file."""
        if obj.raster_file and obj.raster_file.name.lower().endswith(
            (".tif", ".tiff"),
        ):
            try:
                with obj.raster_file.open("rb") as f:
                    img = Image.open(f)
                    img.thumbnail((120, 120))
                    if img.mode == "F":
                        import numpy as np

                        arr = np.array(img)
                        arr = arr - arr.min()
                        if arr.max() > 0:
                            arr = arr / arr.max()
                        arr = (arr * 255).astype("uint8")
                        img = Image.fromarray(arr, mode="L")
                    elif img.mode not in ("L", "RGB"):
                        img = img.convert("RGB")
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    image_base64 = base64.b64encode(buf.getvalue()).decode(
                        "utf-8",
                    )
                    return mark_safe(  # noqa: S308 — base64-encoded PIL PNG, no user input
                        f'<img src="data:image/png;base64,{image_base64}" style="max-width:120px; max-height:120px;" />',
                    )
            except Exception as e:
                return f"Preview unavailable: {e}"
        return "No preview"

    preview.short_description = "Thumbnail"


@admin.register(MicroXRFMeasurement)
class MicroXRFAdmin(
    SampleContextMixin,
    ExportMixin,
    ModelAdmin,
    NestedProjectPermissionMixin,
):
    """Admin for MicroXRFMeasurement with element map inlines."""

    change_form_show_cancel_button = True
    project_path = "sample__location__project"
    list_fullwidth = True
    list_display = ["measurement_date", "method"]
    raw_id_fields = ["sample"]
    inlines = [MicroXRFElementInline]


class MeasurementSeriesAdmin(ModelAdmin):
    """Admin for the MeasurementSeries model."""

    change_form_show_cancel_button = True
    list_display = ["id", "datetime"]
    ordering = ["-datetime"]
    search_fields = ["id"]


admin.site.register(Algorithm, AlgorithmAdmin)
admin.site.register(GrainSize, GrainSizeAdmin)
admin.site.register(GenericMeasurement, GenericMeasurementAdmin)
admin.site.register(MeasurementSeries, MeasurementSeriesAdmin)
admin.site.register(Parameter, ParameterAdmin)
admin.site.register(Counting, CountingAdmin)
admin.site.register(Pollen, PollenAdmin)
admin.site.register(LuminescenceDating, LuminescenceDatingAdmin)
admin.site.register(RadiocarbonDating, RadiocarbonDatingAdmin)
admin.site.register(RawMeasurement, RawMeasurementAdmin)
admin.site.register(RawProcessing, RawProcessingAdmin)
