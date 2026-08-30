"""django-import-export resource classes for the analysis app."""

from __future__ import annotations

from typing import Any

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget, JSONWidget

from field_data.models import Sample

from .models import (
    GRAIN_SIZE_INPUT_FIELDS,
    GRAIN_SIZE_STATS_FIELDS,
    GrainSize,
    LuminescenceDating,
    RadiocarbonDating,
    RawMeasurement,
)


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
    """Import/export resource for GrainSize.

    tech debt A7: originally omitted raw_data/classes/measured_data, so a
    CSV-imported record lost the provenance the single-record admin upload
    path (GrainSizeAdmin.process_file) captures. `source` is deliberately
    NOT a CSV column - it's an editable=False, system-managed field on the
    model (see GrainSize.source), so before_save_instance() forces it to
    "file" for every imported row instead of trusting a CSV column.
    """

    sample = fields.Field(
        column_name="sample",
        attribute="sample",
        widget=ForeignKeyWidget(Sample, field="identifier"),
    )
    raw_data = fields.Field(
        column_name="raw_data",
        attribute="raw_data",
        widget=ForeignKeyWidget(RawMeasurement, field="pk"),
    )
    classes = fields.Field(
        column_name="classes",
        attribute="classes",
        widget=JSONWidget(),
    )
    measured_data = fields.Field(
        column_name="measured_data",
        attribute="measured_data",
        widget=JSONWidget(),
    )

    class Meta:
        """Resource metadata."""

        model = GrainSize
        fields = ("id", *GRAIN_SIZE_INPUT_FIELDS, *GRAIN_SIZE_STATS_FIELDS)
        export_order = fields

    def before_save_instance(
        self,
        instance: GrainSize,
        row: dict[str, Any],
        **kwargs: object,
    ) -> None:
        """Mark every CSV-imported row as file-sourced, like the admin upload path."""
        instance.source = "file"
        super().before_save_instance(instance, row, **kwargs)
