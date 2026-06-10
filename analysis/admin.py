import base64
import io

import matplotlib as mpl
import matplotlib.pyplot as plt
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
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

from prototype.mixins import CreatedUpdatedModelAdminMixin, NestedProjectPermissionMixin

from .models import (
    Algorithm,
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

    def _is_sample_scoped(self, request):
        url_name = getattr(getattr(request, "resolver_match", None), "url_name", "") or ""
        return url_name.startswith("field_data_sample_")

    def _sample_pk_from_add_request(self, request):
        from field_data.utils import extract_sample_pk_from_get
        return extract_sample_pk_from_get(request.GET)

    def changelist_view(self, request, extra_context=None):
        if not self._is_sample_scoped(request):
            sample_pk = request.GET.get("sample__id__exact", "")
            if sample_pk and sample_pk.isdigit():
                model_name = self.model._meta.model_name
                try:
                    url = reverse(f"admin:field_data_sample_{model_name}", args=[sample_pk])
                    return redirect(url)
                except NoReverseMatch:
                    pass
        return super().changelist_view(request, extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        if request.method == "GET" and not self._is_sample_scoped(request):
            sample_pk = self._sample_pk_from_add_request(request)
            if sample_pk:
                model_name = self.model._meta.model_name
                try:
                    url = reverse(f"admin:field_data_sample_{model_name}_add", args=[sample_pk])
                    return redirect(url)
                except NoReverseMatch:
                    pass
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
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

    def get_changeform_initial_data(self, request):
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

    def _redirect_to_sample(self, request, obj):
        if "_save" in request.POST and getattr(obj, "sample_id", None):
            return redirect(reverse("admin:field_data_sample_change", args=[obj.sample_id]))
        return None

    def response_add(self, request, obj, post_url_continue=None):
        r = self._redirect_to_sample(request, obj)
        return r if r else super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        r = self._redirect_to_sample(request, obj)
        return r if r else super().response_change(request, obj)

# ======================
# RAW DATA ADMIN
# ======================


class AlgorithmAdmin(ExportMixin, ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["name", "version", "programming_language"]
    search_fields = ["name", "version"]
    ordering = ["name", "version"]


class RawMeasurementAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
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


class RawProcessingAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
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
    model = PollenCount
    extra = 0


class CountingAdmin(SampleContextMixin, ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    change_form_show_cancel_button = True
    warn_unsaved_form = True
    project_path = "sample__location__project"
    inlines = [PollenCountInline]
    list_display = ["type"]
    list_fullwidth = True
    raw_id_fields = ["sample"]


class PollenAdmin(ExportMixin, ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["name", "token", "name_en"]
    search_fields = ["name", "token", "name_en"]
    ordering = ["name"]


# ======================
# GEOCHRONOLOGY ADMIN
# ======================


class LuminescenceDatingAdmin(SampleContextMixin, ImportExportMixin, CreatedUpdatedModelAdminMixin, NestedProjectPermissionMixin, ModelAdmin):
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
    def age(self, obj):
        if obj.luminescence_age:
            return f"{round(obj.luminescence_age, 2)} ± {round(obj.age_error, 2)}"
        return "—"

    @display(description="Dose rate [Gy/ka]")
    def total_dose_rate(self, obj):
        if obj.dose_rate:
            return f"{round(obj.dose_rate, 2)} ± {round(obj.dose_rate_error, 2)}"
        return "—"

    @display(description="Paleodose [Gy]")
    def paleodose(self, obj):
        if obj.palaeodose_value:
            return f"{round(obj.palaeodose_value, 2)} ± {round(obj.palaeodose_error, 2)}"
        return "—"

    @display(
        label={"Quartz": "success", "Feldspar": "info", "Polymineral": "warning", "Other": "default"},
        description="Mineral",
    )
    def colored_mineral(self, obj):
        return obj.mineral

    @display(
        label={"Burial dating": "info", "Exposure dating": "success", "Other": "warning"},
        description="Approach",
    )
    def colored_dating_approach(self, obj):
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
                    ("instrumental_beta_source_error", "uncertainty_beta_source_calibration"),
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
                    ("dose_rate_measurement_technique", "dose_rate_calculation_software"),
                    ("u_ppm", "u_ppm_error"),
                    ("th_ppm", "th_ppm_error"),
                    ("k_percent", "k_percent_error"),
                    ("water_content_for_dating", "water_content_for_dating_error"),
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

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("sample__location__project")


class RadiocarbonDatingAdmin(
    SampleContextMixin,
    ImportExportMixin,
    ModelAdmin,
    NestedProjectPermissionMixin,
):
    change_form_show_cancel_button = True
    project_path = "sample__location__project"
    raw_id_fields = ["sample"]
    list_fullwidth = True
    list_display = ["lab_id", "lab", "age"]
    ordering = ["-id"]


# ======================
# SEDIMENTOLOGY ADMIN
# ======================


class GenericMeasurementResource(resources.ModelResource):

    class Meta:
        model = GenericMeasurement

        skip_diff = True
        import_id_fields = ("sample",)


class GeochemistryParameterResource(resources.ModelResource):
    class Meta:
        model = Parameter


class GrainSizeImportForm(forms.ModelForm):
    file = forms.FileField(required=False)

    def clean_file(self):
        file = self.cleaned_data.get("file")

        if not file:
            return file

        if not file.name.lower().endswith(".$av"):
            raise ValidationError(_("Invalid file type. Only .$av files are allowed."))

        max_size_mb = 10
        if file.size > max_size_mb * 1024 * 1024:
            raise ValidationError(
                _(
                    f"File size ({file.size / (1024 * 1024):.1f}MB) exceeds maximum allowed size of {max_size_mb}MB.",
                ),
            )

        try:
            file.seek(0)
            first_chunk = file.read(1024)
            file.seek(0)

            if len(first_chunk) == 0:
                raise ValidationError(_("File is empty or corrupted."))
        except Exception as e:
            raise ValidationError(_(f"Unable to read file: {e!s}")) from None

        return file

    class Meta:
        model = GrainSize
        fields = "__all__"


class GrainSizeAdmin(SampleContextMixin, ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
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
        "mean", "mode", "median", "std", "skew", "kurtosis",
        "fwmean", "fwmedian", "fwsd", "fwskew", "fwkurt",
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

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.source == "file":
            readonly += [f for f in self._STAT_FIELDS if f not in readonly]
        return readonly

    @display(label={"L": "success", "C": "info", "S": "warning"}, description="Method")
    def colored_method(self, obj):
        return obj.method

    @display(description="Sample concentration [%]")
    def colored_sample_concentration(self, obj):
        if obj.sample_concentration is None:
            return "N/A"
        color = "success" if 6 <= obj.sample_concentration <= 20 else "danger"
        color = color if color in {"success", "danger", "warning", "info"} else "danger"
        rounded = round(obj.sample_concentration, 1)
        return mark_safe(
            f'<span class="text-{color}-600 dark:text-{color}-400 font-semibold">{rounded} %</span>'
        )

    @admin.display(description="Classes")
    def classes_summary(self, obj):
        if not obj.classes:
            return "—"
        n = len(obj.classes)
        mn = min(obj.classes)
        mx = max(obj.classes)
        return f"{n} classes, {mn}–{mx} µm"

    @admin.display(description="Measured data")
    def measured_data_summary(self, obj):
        if not obj.measured_data:
            return "—"
        n = len(obj.measured_data)
        total = sum(obj.measured_data)
        return f"{n} data points, sum = {round(total, 1)}"

    def save_model(self, request, obj, form, change):
        file = form.cleaned_data.get("file")
        if file:
            self.process_file(file, obj)
            obj.source = "file"
            self.message_user(request, "File uploaded and processed successfully.", messages.SUCCESS)
        super().save_model(request, obj, form, change)

    def process_file(self, file, obj):
        file_path = default_storage.save(f"tmp/{file.name}", ContentFile(file.read()))
        tmp_file = default_storage.path(file_path)

        grain_size_instance = GrainSize.from_file(tmp_file, obj.sample, obj.method)

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

    def plot(self, obj):
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
                x=x, y=-0.1, s=str(x), fontsize=21,
                verticalalignment="top", horizontalalignment="center",
                transform=ax.get_xaxis_transform(),
            )
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return mark_safe(f'<img src="data:image/png;base64,{image_base64}" />')

    plot.short_description = "Grain size distribution"


class GenericMeasurementAdmin(SampleContextMixin, ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
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
    def value_with_error(self, obj):
        if obj.value is None:
            return "—"
        if obj.error:
            return f"{round(obj.value, 4)} ± {round(obj.error, 4)}"
        return round(obj.value, 4)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("method", "parameter")


class ParameterAdmin(ExportMixin, ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["token", "id", "unit"]
    search_fields = ["token"]
    ordering = ["token"]
    resource_classes = [GeochemistryParameterResource]


class MicroXRFElementInline(admin.TabularInline):
    model = MicroXRFElementMap
    hide_title = True
    readonly_fields = ["preview"]
    fields = ["element", "raster_file", "preview"]
    extra = 0

    def preview(self, obj):
        if obj.raster_file and obj.raster_file.name.lower().endswith((".tif", ".tiff")):
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
                    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                    return mark_safe(
                        f'<img src="data:image/png;base64,{image_base64}" style="max-width:120px; max-height:120px;" />',
                    )
            except Exception as e:
                return f"Preview unavailable: {e}"
        return "No preview"

    preview.short_description = "Thumbnail"


@admin.register(MicroXRFMeasurement)
class MicroXRFAdmin(SampleContextMixin, ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    change_form_show_cancel_button = True
    project_path = "sample__location__project"
    list_fullwidth = True
    list_display = ["measurement_date", "method"]
    raw_id_fields = ["sample"]
    inlines = [MicroXRFElementInline]


class MeasurementSeriesAdmin(ModelAdmin):
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
