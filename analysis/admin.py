import base64
import io
import os

import matplotlib
import matplotlib.pyplot as plt
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ExportMixin, ImportExportMixin
from PIL import Image
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter

from prototype.mixins import NestedProjectPermissionMixin

from .models import (
    Algorithm,
    Counting,
    GenericMeasurement,
    GrainSize,
    LuminescenceDating,
    MicroXRFElementMap,
    MicroXRFMeasurement,
    Parameter,
    Pollen,
    PollenCount,
    RadiocarbonDating,
    RawMeasurement,
    RawProcessing,
)

matplotlib.use("Agg")

# ======================
# RAW DATA ADMIN
# ======================


class AlgorithmAdmin(ExportMixin, ModelAdmin):
    list_display = [
        "name",
        "version",
        "programming_language",
    ]


class RawMeasurementAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    project_path = "sample__location__project"  
    list_display = [
        "device",
        "accessories",
        "researcher",
        "file",
        "description",
    ]
    ordering = ["sample__location__project", "sample__location", "sample"]

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
    list_display = [
        "raw_measurement",
    ]


# ======================
# PALEOBOTANY ADMIN
# ======================


class PollenCountInline(TabularInline):
    model = PollenCount
    extra = 0


class CountingAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    project_path = "sample__location__project" 
    inlines = [PollenCountInline]
    list_display = [
        "project",
        "location",
        "sample",
    ]
    ordering = ["sample__location__project", "sample__location", "sample"]

    raw_id_fields = ["sample"]
    list_filter_sheet = False
    list_filter_submit = True
    list_filter = [
        (
            "sample__location__project",
            RelatedDropdownFilter,
        ),
        (
            "sample__location",
            RelatedDropdownFilter,
        ),
    ]

    @admin.display(description="Location")
    def location(self, obj):
        return obj.sample.location

    @admin.display(description="Project")
    def project(self, obj):
        return obj.sample.location.project


class PollenAdmin(ExportMixin, ModelAdmin):
    list_display = [
        "name",
        "token",
        "name_en",
    ]


# ======================
# GEOCHRONOLOGY ADMIN
# ======================


class LuminescenceDatingAdmin(ImportExportMixin, ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = False
    list_fullwidth = False
    list_filter_sheet = True
    list_horizontal_scrollbar_top = False
    list_disable_select_all = False

    list_display = [
        "sample__identifier",
        "laboratory_id",
        "dating_approach",
        "mineral",
        "age",
        "total_dose_rate",
        "paleodose",
    ]

    raw_id_fields = ["sample"]
    list_filter = [
        (
            "sample__location__project",
            RelatedDropdownFilter,
        ),
        (
            "mineral",
            ChoicesDropdownFilter,
        ),
        (
            "dating_approach",
            ChoicesDropdownFilter,
        ),
        (
            "published",
            ChoicesDropdownFilter,
        ),
        (
            "thesis",
            ChoicesDropdownFilter,
        ),
    ]
    list_filter_sheet = False
    list_filter_submit = True

    def age(self, obj):
        if obj.luminescence_age:
            entry = f"{round(obj.luminescence_age, 2)} ± {round(obj.age_error, 2)}"
            return entry
        else:
            return "Not available"

    age.short_description = "Luminescence age [ka]"

    def total_dose_rate(self, obj):
        if obj.dose_rate:
            entry = f"{round(obj.dose_rate, 2)} ± {round(obj.dose_rate_error, 2)}"
            return entry
        else:
            return "Not available"

    total_dose_rate.short_description = "Dose rate [Gy/ka]"

    def paleodose(self, obj):
        if obj.palaeodose_value:
            entry = (
                f"{round(obj.palaeodose_value, 2)} ± {round(obj.palaeodose_error, 2)}"
            )
            return entry
        else:
            return "Not available"

    paleodose.short_description = "Paleodose [Gy]"

    fieldsets = (
        (
            "Main information",
            {
                "classes": ["tab"],
                "fields": (
                    "sample",
                    "laboratory_id",
                    "sample_id_cll",
                    "mineral",
                    "dating_approach",
                    "luminescence_age",
                    "age_error",
                    "signal",
                    "protocol",
                    "palaeodose_value",
                    "palaeodose_error",
                    "dose_rate",
                    "dose_rate_error",
                    "published",
                    "thesis",
                ),
            },
        ),
        (
            "Palaeodoses",
            {
                "classes": ["tab"],
                "fields": (
                    "grain_size_min",
                    "grain_size_max",
                    "aliquot_size",
                    "aliquot_number_used_for_palaeodose",
                    "od_percent",
                    "od_percent_error",
                    "od_gy",
                    "od_gy_error",
                    "age_model",
                    "beta_source_calibration",
                    "instrumental_beta_source_error",
                    "uncertainty_beta_source_calibration",
                    "fading_correction",
                    "g_value",
                    "g_value_error",
                    "Lnat_Lsat_ratio",
                ),
            },
        ),
        (
            "Dosimetry",
            {
                "classes": ["tab"],
                "fields": (
                    "dose_rate_measurement_technique",
                    "dose_rate_calculation_software",
                    "u_ppm",
                    "u_ppm_error",
                    "th_ppm",
                    "th_ppm_error",
                    "k_percent",
                    "k_percent_error",
                    "water_content_for_dating",
                    "water_content_for_dating_error",
                    "a_value",
                    "a_value_error",
                    "alpha_dose_rate",
                    "alpha_dose_rate_error",
                    "beta_dose_rate",
                    "beta_dose_rate_error",
                    "gamma_dose_rate",
                    "gamma_dose_rate_error",
                    "cosmic_dose_rate",
                    "cosmic_dose_rate_error",
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:  
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class RadiocarbonDatingAdmin(
    ImportExportMixin, ModelAdmin, NestedProjectPermissionMixin
):
    project_path = "sample__location__project" 
    raw_id_fields = ["sample"]
    list_filter = [
        (
            "lab",
            ChoicesDropdownFilter,
        ),
        (
            "sample__location__project",
            RelatedDropdownFilter,
        ),
    ]
    list_filter_sheet = False
    list_filter_submit = True
    list_display = [
        "sample",
        "sample__location__project__label",
        "lab",
        "age",
    ]


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

        if not file.name.endswith(".$av"):
            raise ValidationError(_("Invalid file type. Only .$av files are allowed."))

        max_size_mb = 10
        if file.size > max_size_mb * 1024 * 1024:
            raise ValidationError(
                _(
                    f"File size ({file.size / (1024 * 1024):.1f}MB) exceeds maximum allowed size of {max_size_mb}MB."
                )
            )

        try:
            file.seek(0)
            first_chunk = file.read(1024)
            file.seek(0)

            if len(first_chunk) == 0:
                raise ValidationError(_("File is empty or corrupted."))
        except Exception as e:
            raise ValidationError(_(f"Unable to read file: {str(e)}"))

        return file

    class Meta:
        model = GrainSize
        fields = "__all__"


class GrainSizeAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    project_path = "sample__location__project" 
    form = GrainSizeImportForm

    list_display = [
        "sample",
        "location",
        "project",
        "colored_sample_concentration",
    ]

    @admin.display(description="Location")
    def location(self, obj):
        return obj.sample.location

    @admin.display(description="Project")
    def project(self, obj):
        return obj.sample.project

    list_filter = [
        (
            "sample",
            RelatedDropdownFilter,
        ),
        (
            "sample__location",
            RelatedDropdownFilter,
        ),
        (
            "sample__location__project",
            RelatedDropdownFilter,
        ),
        (
            "sample__location__campaign",
            RelatedDropdownFilter,
        ),
    ]
    list_filter_submit = True
    list_filter_sheet = False
    readonly_fields = [
        "classes",
        "colored_sample_concentration",
        "measured_data",
        "clay",
        "fine_silt",
        "medium_silt",
        "coarse_silt",
        "fine_sand",
        "medium_sand",
        "coarse_sand",
        "plot",
    ]
    raw_id_fields = ["sample"]

    fieldsets = (
        (
            "Metadata",
            {
                "classes": ["tab"],
                "fields": (
                    "sample",
                    "sample_weight",
                    "method",
                    "file",
                ),
            },
        ),
        (
            "Data",
            {
                "classes": ["tab"],
                "fields": (
                    "classes",
                    "measured_data",
                    "colored_sample_concentration",
                ),
            },
        ),
        (
            "Classes",
            {
                "classes": ["tab"],
                "fields": (
                    "clay",
                    "fine_silt",
                    "medium_silt",
                    "coarse_silt",
                    "fine_sand",
                    "medium_sand",
                    "coarse_sand",
                ),
            },
        ),
        (
            "Size Stats",
            {
                "classes": ["tab"],
                "fields": (
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

    def save_model(self, request, obj, form, change):
        file = form.cleaned_data.get("file")
        if file:
            self.process_file(file, obj)
            self.message_user(
                request,
                "File uploaded and processed successfully",
                messages.SUCCESS,
            )
        super().save_model(request, obj, form, change)

    def process_file(self, file, obj):
        file_path = default_storage.save(f"tmp/{file.name}", ContentFile(file.read()))
        tmp_file = os.path.join(default_storage.location, file_path)

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

    def colored_sample_concentration(self, obj):
        if obj.sample_concentration is None:
            return "N/A"
        if obj.sample_concentration >= 6 and obj.sample_concentration <= 20:
            color = "green"
        else:
            color = "red"
        rounded_concentration = round(obj.sample_concentration, 1)
        return mark_safe(
            f'<span style="color: {color};">{rounded_concentration}</span>'
        )

    colored_sample_concentration.short_description = "Sample concentration [%]"

    def plot(self, obj):
        if not obj.measured_data or not obj.classes:
            return "No data available for plotting"
        fig, ax = plt.subplots(figsize=(30, 10))
        ax.plot(obj.classes, obj.measured_data, marker="")
        ax.set_xscale("log")
        ax.set_xlim(0.04, 2000)
        ax.set_xlabel("Grain Size (μm)", fontsize=21)
        ax.set_ylabel("GSD (%)", fontsize=21)
        ax.tick_params(axis="both", which="major", labelsize=12)

        for x in [0.2, 0.63, 2, 6.3, 20, 63, 200, 630]:
            ax.axvline(x=x, color="black", linestyle="--", linewidth=0.5, label=x)
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
        return mark_safe(f'<img src="data:image/png;base64,{image_base64}" />')

    plot.allow_tags = True
    plot.short_description = "Plot of Measured Data vs Classes"


class GenericMeasurementAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    project_path = "sample__location__project"  
    resource_classes = [GenericMeasurementResource]
    list_display = [
        "sample__location__project__label",
        "sample__identifier",
        "method",
        "parameter__token",
        "value",
        "id",
    ]

    list_filter = [
        (
            "sample__location__project",
            RelatedDropdownFilter,
        ),
        (
            "method",
            RelatedDropdownFilter,
        ),
        (
            "parameter",
            RelatedDropdownFilter,
        ),
    ]
    list_filter_sheet = False
    list_filter_submit = True


class ParameterAdmin(ExportMixin, ModelAdmin):
    list_display = [
        "token",
        "id",
        "unit",
    ]
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
                        f'<img src="data:image/png;base64,{image_base64}" style="max-width:120px; max-height:120px;" />'
                    )
            except Exception as e:
                return f"Fehler beim Laden: {e}"
        return "No preview"

    preview.short_description = "Thumbnail"


@admin.register(MicroXRFMeasurement)
class MicroXRFAdmin(ExportMixin, ModelAdmin, NestedProjectPermissionMixin):
    project_path = "sample__location__project"  # Define the path to project
    list_display = [
        "sample",
        "sample__project",
    ]
    list_filter = [
        (
            "sample__project",
            RelatedDropdownFilter,
        ),
        (
            "sample__location",
            RelatedDropdownFilter,
        ),
    ]
    list_filter_sheet = False
    list_filter_submit = True
    raw_id_fields = ["sample"]
    inlines = [MicroXRFElementInline]


admin.site.register(Algorithm, AlgorithmAdmin)
admin.site.register(GrainSize, GrainSizeAdmin)
admin.site.register(GenericMeasurement, GenericMeasurementAdmin)
admin.site.register(Parameter, ParameterAdmin)
admin.site.register(Counting, CountingAdmin)
admin.site.register(Pollen, PollenAdmin)
admin.site.register(LuminescenceDating, LuminescenceDatingAdmin)
admin.site.register(RadiocarbonDating, RadiocarbonDatingAdmin)
admin.site.register(RawMeasurement, RawMeasurementAdmin)
admin.site.register(RawProcessing, RawProcessingAdmin)
