"""django-import-export resource classes for the analysis app."""

from __future__ import annotations

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from field_data.models import Sample

from .models import GrainSize, LuminescenceDating, RadiocarbonDating


class LuminescenceDatingResource(resources.ModelResource):
    """Import/export resource for LuminescenceDating."""

    sample = fields.Field(
        column_name="sample",
        attribute="sample",
        widget=ForeignKeyWidget(Sample, field="identifier"),
    )

    class Meta:
        """Resource metadata."""

        model = LuminescenceDating
        fields = (
            "id",
            "sample",
            "laboratory_id",
            "sample_id_cll",
            "mineral",
            "dating_approach",
            "signal",
            "protocol",
            "luminescence_age",
            "age_error",
            "palaeodose_value",
            "palaeodose_error",
            "dose_rate",
            "dose_rate_error",
            "age_model",
            "grain_size_min",
            "grain_size_max",
            "aliquot_size",
            "aliquot_number_used_for_palaeodose",
            "od_percent",
            "od_percent_error",
            "od_gy",
            "od_gy_error",
            "beta_source_calibration",
            "instrumental_beta_source_error",
            "uncertainty_beta_source_calibration",
            "fading_correction",
            "g_value",
            "g_value_error",
            "Lnat_Lsat_ratio",
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
            "published",
            "year_of_publication",
            "thesis",
            "comments",
        )
        export_order = (
            "id",
            "sample",
            "laboratory_id",
            "sample_id_cll",
            "mineral",
            "dating_approach",
            "signal",
            "protocol",
            "luminescence_age",
            "age_error",
            "palaeodose_value",
            "palaeodose_error",
            "dose_rate",
            "dose_rate_error",
            "age_model",
            "grain_size_min",
            "grain_size_max",
            "aliquot_size",
            "aliquot_number_used_for_palaeodose",
            "od_percent",
            "od_percent_error",
            "od_gy",
            "od_gy_error",
            "beta_source_calibration",
            "instrumental_beta_source_error",
            "uncertainty_beta_source_calibration",
            "fading_correction",
            "g_value",
            "g_value_error",
            "Lnat_Lsat_ratio",
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
            "published",
            "year_of_publication",
            "thesis",
            "comments",
        )


class RadiocarbonDatingResource(resources.ModelResource):
    """Import/export resource for RadiocarbonDating."""

    sample = fields.Field(
        column_name="sample",
        attribute="sample",
        widget=ForeignKeyWidget(Sample, field="identifier"),
    )

    class Meta:
        """Resource metadata."""

        model = RadiocarbonDating
        fields = ("id", "sample", "lab", "lab_id", "age")
        export_order = ("id", "sample", "lab", "lab_id", "age")


class GrainSizeResource(resources.ModelResource):
    """Import/export resource for GrainSize."""

    sample = fields.Field(
        column_name="sample",
        attribute="sample",
        widget=ForeignKeyWidget(Sample, field="identifier"),
    )

    class Meta:
        """Resource metadata."""

        model = GrainSize
        fields = (
            "id",
            "sample",
            "sample_weight",
            "sample_concentration",
            "method",
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
        )
        export_order = (
            "id",
            "sample",
            "sample_weight",
            "sample_concentration",
            "method",
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
        )
