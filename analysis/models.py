from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Self
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from bibliography.models import Reference
from field_data.models import Sample
from laboratory.models import Accessory, Device, Method
from prototype.models import BaseModel, Project, Researcher


class Algorithm(models.Model):
    """Represents an analysis algorithm.

    Attributes:
        name (CharField): Name of the algorithm.
        version (CharField): Version of the algorithm.
        description (TextField): Description of the algorithm.
        link (URLField): Link to the algorithm resource.
        file (FileField): File containing the algorithm.
        programming_language (CharField): Programming language used.
    """

    name = models.CharField(max_length=100)
    version = models.CharField(max_length=10)
    description = models.TextField(blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    file = models.FileField(upload_to="analysis/algorithms/", blank=True, null=True)
    CHOICES = [
        ("Python", "Python"),
        ("R", "R"),
        ("MATLAB", "MATLAB"),
        ("Julia", "Julia"),
        ("Other", "Other"),
    ]
    programming_language = models.CharField(
        max_length=50,
        choices=CHOICES,
    )

    def __str__(self):
        return self.name


class RawMeasurement(BaseModel):
    """Raw data model for storing uploaded files.

    Attributes:
        project (ForeignKey): Project associated with the measurement.
        sample (ManyToManyField): Samples associated with the measurement.
        device (ForeignKey): Device used for measurement.
        accessories (ForeignKey): Accessories used.
        researcher (ForeignKey): Researcher who performed the measurement.
        file (FileField): Uploaded raw data file.
        description (TextField): Description of the measurement.
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="analysis_raw_data",
    )
    sample = models.ManyToManyField(Sample, related_name="analysis_raw_data")
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="analysis_raw_data",
    )
    accessories = models.ForeignKey(
        Accessory,
        on_delete=models.CASCADE,
        related_name="analysis_raw_data",
        blank=True,
        null=True,
    )
    researcher = models.ForeignKey(
        Researcher,
        on_delete=models.CASCADE,
        related_name="analysis_raw_data",
    )
    file = models.FileField(upload_to="analysis/raw_data/")
    description = models.TextField(blank=True, null=True)

    def filename(self):
        return Path.name(self.file.name)

    def __str__(self):
        return f"{self.sample} - {self.filename()}"


class RawProcessing(BaseModel):
    """Model for storing processed data derived from raw measurements.

    Attributes:
        raw_measurement (ForeignKey): Reference to the raw measurement.
        processed_file (FileField): File containing processed data.
        processing_description (TextField): Description of the processing.
        processed_by (ForeignKey): Researcher who processed the data.
        processing_date (DateField): Date of processing.
        preparation_algorithm (ForeignKey): Algorithm used for preparation.
        evaluation_algorithm (ForeignKey): Algorithm used for evaluation.
        publication (ForeignKey): Reference to publication.
    """

    raw_measurement = models.ForeignKey(
        RawMeasurement,
        on_delete=models.CASCADE,
        related_name="analysis_raw_processing",
    )

    processed_file = models.FileField(upload_to="analysis/processed_data/")
    processing_description = models.TextField(blank=True, null=True)

    processed_by = models.ForeignKey(
        Researcher,
        on_delete=models.CASCADE,
        related_name="analysis_processed_data",
    )
    processing_date = models.DateField(auto_now_add=True)

    preparation_algorithm = models.ForeignKey(
        Algorithm,
        on_delete=models.SET_NULL,
        related_name="analysis_processed_data",
        blank=True,
        null=True,
    )
    evaluation_algorithm = models.ForeignKey(
        Algorithm,
        on_delete=models.SET_NULL,
        related_name="analysis_evaluated_data",
        blank=True,
        null=True,
    )

    publication = models.ForeignKey(
        Reference,
        on_delete=models.SET_NULL,
        related_name="analysis_processed_data",
        blank=True,
        null=True,
    )

    def processed_filename(self):
        return Path.name(self.processed_file.name)

    def __str__(self):
        return f"Processed data for {self.raw_measurement} - {self.processed_filename()}"


# ======================
# PALEOBOTANY MODELS
# ======================


class Counting(BaseModel):
    """Counting model for paleobotany analysis.

    Attributes:
        sample (ForeignKey): Sample associated with the counting.
        raw_data (ForeignKey): Raw measurement data.
        type (CharField): Type of counting (Percent or Absolute numbers).
    """

    sample = models.ForeignKey(
        Sample,
        on_delete=models.RESTRICT,
        related_name="analysis_countings",
    )
    raw_data = models.ForeignKey(
        RawMeasurement,
        on_delete=models.RESTRICT,
        related_name="analysis_counting_raw_data",
        blank=True,
        null=True,
    )
    COUNTING_CHOICES = [
        (
            "Percent",
            "Percent",
        ),
        (
            "Absolute numbers",
            "Absolute numbers",
        ),
    ]
    type = models.CharField(choices=COUNTING_CHOICES, max_length=50)

    class Meta:
        verbose_name = "Counting"
        verbose_name_plural = "Countings"

    def __str__(self):
        return f"{self.sample}"


class Pollen(BaseModel):
    """Pollen species model for paleobotany analysis.

    Attributes:
        name (CharField): Name in Latin.
        token (CharField): Short token for the pollen.
        name_en (CharField): Name in English.
        name_german (CharField): Name in German.
        name_nor (CharField): Name in Norwegian.
    """

    name = models.CharField(max_length=250, help_text="Name in Latin")
    token = models.CharField(max_length=5)
    name_en = models.CharField(
        max_length=250,
        help_text="Name in English",
        verbose_name="English name",
        blank=True,
    )
    name_german = models.CharField(
        max_length=250,
        help_text="Name in German",
        verbose_name="German name",
        blank=True,
    )
    name_nor = models.CharField(
        max_length=250,
        help_text="Name in Norwegian",
        verbose_name="Norwegian name",
        blank=True,
    )

    class Meta:
        verbose_name = "Pollen"
        verbose_name_plural = "Pollen"

    def __str__(self):
        return f"{self.name}"


class PollenCount(BaseModel):
    """Pollen count model linking counting and pollen species.

    Attributes:
        counting (ForeignKey): Reference to Counting.
        pollen (ForeignKey): Reference to Pollen.
        number (IntegerField): Number of pollen counted.
    """

    counting = models.ForeignKey(
        Counting,
        on_delete=models.RESTRICT,
        related_name="analysis_pollen_counts",
    )
    pollen = models.ForeignKey(
        Pollen,
        on_delete=models.RESTRICT,
        related_name="analysis_pollen_counts",
    )
    number = models.IntegerField()

    class Meta:
        verbose_name = "Pollen Count"
        verbose_name_plural = "Pollen Counts"

    def __str__(self):
        return f"{self.counting} - {self.pollen}"


# ======================
# GEOCHRONOLOGY MODELS
# ======================


def current_year():
    return datetime.datetime.now(tz=ZoneInfo("Europe/Berlin")).date().year


def max_value_current_year(value):
    return MaxValueValidator(current_year())(value)


class LuminescenceDating(BaseModel):
    """Model representing luminescence dating information for a sample.

    Attributes:
        laboratory_id (CharField): Laboratory identifier.
        sample (ForeignKey): Sample being dated.
        raw_data (ForeignKey): Raw measurement data.
        sample_id_cll (CharField): Sample ID CLL.
        mineral (CharField): Mineral type.
        dating_approach (CharField): Dating approach.
        luminescence_age (DecimalField): Age in kiloannum.
        age_error (DecimalField): Error in age.
        signal (CharField): Signal type.
        protocol (CharField): Protocol used.
        palaeodose_value (DecimalField): Palaeodose value.
        palaeodose_error (DecimalField): Error in palaeodose.
        dose_rate (DecimalField): Dose rate.
        dose_rate_error (DecimalField): Error in dose rate.
        published (BooleanField): Publication status.
        year_of_publication (PositiveIntegerField): Year of publication.
        thesis (CharField): Thesis type.
        comments (TextField): Additional comments.
        grain_size_min (IntegerField): Minimum grain size.
        grain_size_max (IntegerField): Maximum grain size.
        aliquot_size (CharField): Aliquot size.
        aliquot_number_used_for_palaeodose (IntegerField): Number of aliquots used.
        od_percent (DecimalField): Overdispersion percent.
        od_percent_error (DecimalField): Error in overdispersion percent.
        od_gy (DecimalField): Overdispersion in Gy.
        od_gy_error (DecimalField): Error in overdispersion Gy.
        age_model (CharField): Age model used.
        beta_source_calibration (CharField): Beta source calibration.
        instrumental_beta_source_error (DecimalField): Instrumental error.
        uncertainty_beta_source_calibration (PositiveIntegerField): Uncertainty in calibration.
        fading_correction (BooleanField): Fading correction applied.
        g_value (DecimalField): g-value.
        g_value_error (DecimalField): Error in g-value.
        Lnat_Lsat_ratio (DecimalField): L_na/L_sat ratio.
        dose_rate_measurement_technique (CharField): Dose rate measurement technique.
        dose_rate_calculation_software (CharField): Dose rate calculation software.
        u_ppm (DecimalField): Uranium concentration.
        u_ppm_error (DecimalField): Error in uranium concentration.
        th_ppm (DecimalField): Thorium concentration.
        th_ppm_error (DecimalField): Error in thorium concentration.
        k_percent (DecimalField): Potassium concentration.
        k_percent_error (DecimalField): Error in potassium concentration.
        water_content_for_dating (DecimalField): Water content for dating.
        water_content_for_dating_error (DecimalField): Error in water content.
        a_value (DecimalField): a-value.
        a_value_error (DecimalField): Error in a-value.
        alpha_dose_rate (DecimalField): Alpha dose rate.
        alpha_dose_rate_error (DecimalField): Error in alpha dose rate.
        beta_dose_rate (DecimalField): Beta dose rate.
        beta_dose_rate_error (DecimalField): Error in beta dose rate.
        gamma_dose_rate (DecimalField): Gamma dose rate.
        gamma_dose_rate_error (DecimalField): Error in gamma dose rate.
        cosmic_dose_rate (DecimalField): Cosmic dose rate.
        cosmic_dose_rate_error (DecimalField): Error in cosmic dose rate.
    """

    laboratory_id = models.CharField(
        max_length=15,
        verbose_name="Laboratory ID",
        blank=True,
    )
    sample = models.ForeignKey(
        Sample,
        on_delete=models.RESTRICT,
        related_name="luminescence_datings",
    )
    raw_data = models.ForeignKey(
        RawMeasurement,
        on_delete=models.RESTRICT,
        related_name="analysis_luminescence_datings",
        blank=True,
        null=True,
    )
    sample_id_cll = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="Sample ID CLL",
    )

    CHOICES_MINERAL = [
        ("Quartz", "Quartz"),
        ("Feldspar", "Feldspar"),
        ("Polymineral", "Polymineral"),
        ("Other", "Other"),
    ]
    mineral = models.CharField(
        max_length=11,
        choices=CHOICES_MINERAL,
        blank=True,
    )

    CHOICES_DATING_APPROACH = [
        ("Burial dating", "Burial dating"),
        ("Exposure dating", "Exposure dating"),
        ("Other", "Other"),
    ]
    dating_approach = models.CharField(
        max_length=18,
        choices=CHOICES_DATING_APPROACH,
        blank=True,
    )

    luminescence_age = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="ka",
        blank=True,
        null=True,
    )

    age_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="ka, 1σ",
        blank=True,
        null=True,
    )

    signal = models.CharField(
        max_length=30,
        blank=True,
        help_text="BSL/IRSL/pIRSL/TL/…",
    )
    protocol = models.CharField(
        max_length=30,
        blank=True,
        help_text="SAR/MAAD/…",
    )

    palaeodose_value = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Gy",
        blank=True,
        null=True,
        verbose_name="Palaeodose",
    )

    palaeodose_error = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Gy, 1σ",
        blank=True,
        null=True,
    )

    dose_rate = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    dose_rate_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Gy/ka, 1σ",
        blank=True,
        null=True,
    )

    published = models.BooleanField(
        default=False,
    )

    year_of_publication = models.PositiveIntegerField(
        default=2025,
        validators=[MinValueValidator(1984), MaxValueValidator(current_year())],
        blank=True,
        null=True,
    )

    CHOICES_THESIS = [
        ("BSc", "BSc"),
        ("MSc", "MSc"),
        ("PhD", "PhD"),
        ("None", "None"),
    ]
    thesis = models.CharField(
        max_length=4,
        choices=CHOICES_THESIS,
        default="None",
        blank=True,
    )

    comments = models.TextField(
        blank=True,
        null=True,
    )

    grain_size_min = models.IntegerField(
        blank=True,
        null=True,
    )

    grain_size_max = models.IntegerField(
        blank=True,
        null=True,
    )

    aliquot_size = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    aliquot_number_used_for_palaeodose = models.IntegerField(
        blank=True,
        null=True,
    )

    od_percent = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="%",
        blank=True,
        null=True,
    )

    od_percent_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="%",
        blank=True,
        null=True,
    )

    od_gy = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Gy",
        blank=True,
        null=True,
    )

    od_gy_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Gy",
        blank=True,
        null=True,
    )

    age_model = models.CharField(
        max_length=30,
        blank=True,
        help_text="CAM/MAM/AM/FMM/…",
    )

    beta_source_calibration = models.CharField(
        max_length=30,
        blank=True,
        default="2019-2",
    )

    instrumental_beta_source_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        blank=True,
        null=True,
    )

    uncertainty_beta_source_calibration = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    fading_correction = models.BooleanField(
        default=False,
        blank=True,
        null=True,
    )

    g_value = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="%/dec",
        blank=True,
        null=True,
    )

    g_value_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="%/dec",
        blank=True,
        null=True,
    )

    Lnat_Lsat_ratio = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="L_na/L_sat",
        verbose_name="L_na/L_sat-ratio",
        blank=True,
        null=True,
    )

    dose_rate_measurement_technique = models.CharField(
        max_length=50,
        blank=True,
    )

    dose_rate_calculation_software = models.CharField(
        max_length=30,
        blank=True,
    )

    u_ppm = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="ppm",
        blank=True,
        null=True,
    )

    u_ppm_error = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        help_text="ppm",
        blank=True,
        null=True,
    )

    th_ppm = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="ppm",
        blank=True,
        null=True,
    )

    th_ppm_error = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        help_text="ppm",
        blank=True,
        null=True,
    )

    k_percent = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        help_text="%",
        blank=True,
        null=True,
    )

    k_percent_error = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        help_text="%",
        blank=True,
        null=True,
    )

    water_content_for_dating = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="%",
        blank=True,
        null=True,
    )

    water_content_for_dating_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="%",
        blank=True,
        null=True,
    )

    a_value = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
    )

    a_value_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
    )

    alpha_dose_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    alpha_dose_rate_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    beta_dose_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    beta_dose_rate_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    gamma_dose_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    gamma_dose_rate_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    cosmic_dose_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    cosmic_dose_rate_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    def __str__(self):
        mineral_str = self.mineral or "Unknown"
        if self.pk:
            lab_id = self.laboratory_id or f"ID-{self.pk}"
        else:
            lab_id = self.laboratory_id or "Unsaved"
        return f"{lab_id} {mineral_str}"


class RadiocarbonDating(BaseModel):
    """Represents radiocarbon dating information for a sample.

    Attributes:
        sample (ForeignKey): Sample being dated.
        raw_data (ForeignKey): Raw measurement data.
        lab (CharField): Laboratory name.
        lab_id (CharField): Laboratory identifier for the sample.
        age (DecimalField): Age in kiloannum.
    """

    LAB_CHOICES = [
        ("Poznań", "Poznań"),
        ("Beta Analytics", "Beta Analytics"),
        ("Other", "Other"),
    ]
    sample = models.ForeignKey(
        Sample,
        on_delete=models.RESTRICT,
        related_name="analysis_radiocarbon_datings",
    )
    raw_data = models.ForeignKey(
        RawMeasurement,
        on_delete=models.RESTRICT,
        related_name="analysis_radiocarbon_raw_data",
        blank=True,
        null=True,
    )
    lab = models.CharField(max_length=30, choices=LAB_CHOICES)
    lab_id = models.CharField(max_length=30)
    age = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        help_text="ka",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.lab_id} ({self.age} ka)"


CLASSES = [
    0.040,
    0.044,
    0.048,
    0.053,
    0.058,
    0.064,
    0.070,
    0.077,
    0.084,
    0.093,
    0.102,
    0.112,
    0.122,
    0.134,
    0.148,
    0.162,
    0.178,
    0.195,
    0.214,
    0.235,
    0.258,
    0.284,
    0.311,
    0.342,
    0.375,
    0.412,
    0.452,
    0.496,
    0.545,
    0.598,
    0.657,
    0.721,
    0.791,
    0.869,
    0.953,
    1.047,
    1.149,
    1.261,
    1.385,
    1.520,
    1.669,
    1.832,
    2.010,
    2.207,
    2.423,
    2.660,
    2.920,
    3.206,
    3.519,
    3.862,
    4.241,
    4.656,
    5.111,
    5.611,
    6.158,
    6.761,
    7.421,
    8.147,
    8.944,
    9.819,
    10.78,
    11.83,
    12.99,
    14.26,
    15.65,
    17.17,
    18.86,
    20.70,
    22.73,
    24.95,
    27.38,
    30.07,
    33.00,
    36.24,
    39.77,
    43.66,
    47.93,
    52.63,
    57.77,
    63.41,
    69.62,
    76.43,
    83.90,
    92.09,
    101.1,
    111.0,
    121.8,
    133.7,
    146.8,
    161.2,
    176.8,
    194.2,
    213.2,
    234.1,
    256.8,
    282.1,
    309.6,
    339.8,
    373.1,
    409.6,
    449.7,
    493.6,
    541.9,
    594.9,
    653.0,
    716.9,
    786.9,
    863.9,
    948.2,
    1041,
    1143,
    1255,
    1377,
    1512,
    1660,
    1822,
    2000,
    2800,
    4000,
    5600,
    8000,
    11200,
    16000,
    22400,
    31500,
    45000,
    63000,
    75000,
]


def default_classes():
    return list(CLASSES)


class Parameter(BaseModel):
    """Represents a physical parameter for measurement.

    Attributes:
        name (CharField): Name of the parameter.
        token (CharField): Short token for the parameter.
        unit (CharField): Physical unit.
        minimal_limit (FloatField): Minimal limit for the parameter.
        maximal_limit (FloatField): Maximal limit for the parameter.
        classes (JSONField): Classes for unstructured list data.
    """

    name = models.CharField(max_length=40)
    token = models.CharField(max_length=10)
    UNIT_CHOICES = [
        (
            "mg/kg",
            "mg/kg",
        ),
        (
            "Percent",
            "Percent",
        ),
        (
            "no dimension",
            "no dimension",
        ),
    ]
    unit = models.CharField(
        max_length=40,
        verbose_name="Physical unit",
        choices=UNIT_CHOICES,
    )
    minimal_limit = models.FloatField(
        blank=True,
        null=True,
    )
    maximal_limit = models.FloatField(
        blank=True,
        null=True,
    )
    classes = models.JSONField(
        blank=True,
        null=True,
        help_text="This field is for determining the classes of unstructured list data.",
    )

    def __str__(self):
        return f"{self.name} - [{self.unit}]"


class MeasurementSeries(BaseModel):
    """Represents a series of measurements.

    Attributes:
        datetime (DateTimeField): Date and time of the measurement series.
    """

    datetime = models.DateTimeField()


class GenericMeasurement(BaseModel):
    """Lists all distinct generic measurements, independent of measured results.

    Attributes:
        sample (ForeignKey): Sample associated with the measurement.
        raw_data (ForeignKey): Raw measurement data.
        MeasurementSeries (ForeignKey): Measurement series.
        sample_weight (FloatField): Weight of the sample.
        method (ForeignKey): Method used for measurement.
        parameter (ForeignKey): Parameter measured.
        value (FloatField): Measured value.
        error (FloatField): Error in measurement.
    """

    sample = models.ForeignKey(
        Sample,
        related_name="generic_measurements",
        on_delete=models.CASCADE,
    )
    raw_data = models.ForeignKey(
        RawMeasurement,
        on_delete=models.RESTRICT,
        related_name="generic_measurements",
        blank=True,
        null=True,
    )
    MeasurementSeries = models.ForeignKey(
        MeasurementSeries,
        related_name="generic_measurements",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    sample_weight = models.FloatField(
        blank=True,
        null=True,
    )
    method = models.ForeignKey(
        Method,
        on_delete=models.RESTRICT,
        related_name="generic_measurements",
    )
    parameter = models.ForeignKey(
        Parameter,
        related_name="generic_measurements",
        on_delete=models.RESTRICT,
    )
    value = models.FloatField(
        blank=True,
        null=True,
    )
    error = models.FloatField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.sample} - {self.method} - {self.parameter}"


class GrainSize(BaseModel):
    """Represents the grain size distribution of a sediment sample.

    Attributes:
        sample (ForeignKey): Reference to the Sample model.
        raw_data (ForeignKey): Raw measurement data.
        sample_weight (FloatField): Weight of the sample.
        sample_concentration (FloatField): Concentration of the sample.
        method (CharField): Method used for grain size measurement.
        classes (JSONField): Classes of the raw grain size measurement.
        measured_data (JSONField): Raw grain size measurement data.
        clay (FloatField): Percentage of clay.
        fine_silt (FloatField): Percentage of fine silt.
        medium_silt (FloatField): Percentage of medium silt.
        coarse_silt (FloatField): Percentage of coarse silt.
        fine_sand (FloatField): Percentage of fine sand.
        medium_sand (FloatField): Percentage of medium sand.
        coarse_sand (FloatField): Percentage of coarse sand.
        mean (FloatField): Mean grain size.
        mode (FloatField): Mode grain size.
        median (FloatField): Median grain size.
        std (FloatField): Standard deviation.
        skew (FloatField): Skewness.
        kurtosis (FloatField): Kurtosis.
        fwmean (FloatField): Folk & Ward mean.
        fwmedian (FloatField): Folk & Ward median.
        fwsd (FloatField): Folk & Ward standard deviation.
        fwskew (FloatField): Folk & Ward skewness.
        fwkurt (FloatField): Folk & Ward kurtosis.
    """

    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name="grain_sizes",
    )
    raw_data = models.ForeignKey(
        RawMeasurement,
        on_delete=models.RESTRICT,
        related_name="generic_grain_sizes",
        blank=True,
        null=True,
    )
    sample_weight = models.FloatField(
        blank=True,
        null=True,
    )
    sample_concentration = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Sample concentration [%]",
    )
    CHOICES = [
        ("L", "Laser diffraction"),
        ("C", "Camsizer"),
        ("S", "Sieves"),
    ]
    method = models.CharField(max_length=40, choices=CHOICES)
    classes = models.JSONField(
        blank=False,
        null=False,
        help_text="This field is for determining the classes of the raw grain size measurement.",
        default=default_classes,
    )
    measured_data = models.JSONField(
        blank=True,
        null=True,
        help_text="This field contains the raw grain size measurement data.",
    )
    clay = models.FloatField(
        blank=True,
        null=True,
    )
    fine_silt = models.FloatField(
        blank=True,
        null=True,
    )
    medium_silt = models.FloatField(
        blank=True,
        null=True,
    )
    coarse_silt = models.FloatField(
        blank=True,
        null=True,
    )
    fine_sand = models.FloatField(
        blank=True,
        null=True,
    )
    medium_sand = models.FloatField(
        blank=True,
        null=True,
    )
    coarse_sand = models.FloatField(
        blank=True,
        null=True,
    )

    mean = models.FloatField(
        blank=True,
        null=True,
    )
    mode = models.FloatField(
        blank=True,
        null=True,
    )
    median = models.FloatField(
        blank=True,
        null=True,
    )

    std = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Standard Deviation",
    )
    skew = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Skewness",
    )
    kurtosis = models.FloatField(
        blank=True,
        null=True,
    )

    fwmean = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Folk & Ward Mean",
    )

    fwmedian = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Folk & Ward Median",
    )
    fwsd = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Folk & Ward Standard Deviation",
    )
    fwskew = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Folk & Ward Skewness",
    )

    fwkurt = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Folk & Ward Kurtosis",
    )

    def _reclassify(self) -> tuple[float, float, float, float, float, float, float]:
        if isinstance(self.measured_data, str):
            self.measured_data = json.loads(self.measured_data)
        elif isinstance(self.measured_data, list):
            pass
        else:
            raise (TypeError("Measured data must be a string or a list."))
        self.clay = 0
        self.fine_silt = 0
        self.medium_silt = 0
        self.coarse_silt = 0
        self.fine_sand = 0
        self.medium_sand = 0
        self.coarse_sand = 0

        for item, data in enumerate(zip(self.classes, self.measured_data)):
            if item < 2:
                self.clay += data
            elif item < 6.3:
                self.fine_silt += data
            elif item < 20:
                self.medium_silt += data
            elif item < 63:
                self.coarse_silt += data
            elif item < 200:
                self.fine_sand += data
            elif item < 630:
                self.medium_sand += data
            elif item < 2000:
                self.coarse_sand += data

        total = sum(self.measured_data)
        self.clay = self.clay / total * 100
        self.fine_silt = self.fine_silt / total * 100
        self.medium_silt = self.medium_silt / total * 100
        self.coarse_silt = self.coarse_silt / total * 100
        self.fine_sand = self.fine_sand / total * 100
        self.medium_sand = self.medium_sand / total * 100
        self.coarse_sand = self.coarse_sand / total * 100

        return (
            self.fine_silt,
            self.medium_silt,
            self.coarse_silt,
            self.fine_sand,
            self.medium_sand,
            self.coarse_sand,
            self.clay,
        )

    def save(self, *args, **kwargs):
        if self.classes is not None and self.measured_data is not None:
            (
                self.fine_silt,
                self.medium_silt,
                self.coarse_silt,
                self.fine_sand,
                self.medium_sand,
                self.coarse_sand,
                self.clay,
            ) = self._reclassify()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.sample) + ", " + str(self.method)

    class Meta:
        verbose_name_plural = "Grain size"

    @classmethod
    def from_file(cls, file_path, sample, method) -> Self:
        """Create an instance of the class from a file.

        Args:
            file_path (str): The path to the file to read.
            sample (str): The sample identifier.
            method (str): The method used for measurement.

        Returns:
            An instance of the class with data populated from the file.
        The file should have sections denoted by square brackets, e.g., [CLASSES] and [MEASURED_DATA].
        The data under [CLASSES] should be float values representing different classes.
        The data under [MEASURED_DATA] should be float values representing measured data.
        """
        with Path.open(file_path, encoding="latin-1", errors="ignore") as file:
            lines = file.readlines()

        classes = []
        measured_data = []
        concentration = []
        current_block = None
        mean = None
        mode = None
        median = None
        std = None
        skew = None
        kurtosis = None
        fwmean = None
        fwmedian = None
        fwsd = None
        fwskew = None
        fwkurt = None

        for line in lines:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current_block = line[1:-1]
            elif current_block == "#Bindiam":
                try:
                    classes.append(float(line))
                except ValueError:
                    continue
            elif current_block == "#Binheight":
                try:
                    measured_data.append(float(line))
                except ValueError:
                    continue
            elif current_block in ["Size0", "Size1", "Size2"]:
                try:
                    key, value = line.split("=")
                    if key.strip() == "Obs":
                        concentration.append(float(value.strip()))
                except ValueError:
                    continue

            elif current_block == "SizeStats":
                try:
                    key, value = line.split("=")
                    if key.strip() == "Mean":
                        mean = float(value.strip())
                    elif key.strip() == "Mode":
                        mode = float(value.strip())
                    elif key.strip() == "Median":
                        median = float(value.strip())
                    elif key.strip() == "SD":
                        std = float(value.strip())
                    elif key.strip() == "Skew":
                        skew = float(value.strip())
                    elif key.strip() == "Kurtosis":
                        kurtosis = float(value.strip())
                    elif key.strip() == "FWMean":
                        fwmean = float(value.strip())
                    elif key.strip() == "FWMedian":
                        fwmedian = float(value.strip())
                    elif key.strip() == "FWSD":
                        fwsd = float(value.strip())
                    elif key.strip() == "FWSkew":
                        fwskew = float(value.strip())
                    elif key.strip() == "FWKurt":
                        fwkurt = float(value.strip())
                except ValueError:
                    continue

        try:
            sample_concentration = sum(concentration) / len(concentration)
        except (ZeroDivisionError, TypeError):
            raise ValueError("No concentration data found in the file.") from None

        return cls(
            sample=sample,
            method=method,
            classes=classes,
            measured_data=measured_data,
            sample_concentration=sample_concentration,
            mean=mean,
            mode=mode,
            median=median,
            std=std,
            skew=skew,
            kurtosis=kurtosis,
            fwmean=fwmean,
            fwmedian=fwmedian,
            fwsd=fwsd,
            fwskew=fwskew,
            fwkurt=fwkurt,
        )


class MicroXRFMeasurement(BaseModel):
    """Represents a MicroXRF measurement for a sample.

    Attributes:
        sample (ForeignKey): Sample measured.
        measurement_date (DateField): Date of measurement.
        method (ForeignKey): Method or device used.
        notes (TextField): Additional notes.
    """

    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name="microxrf_measurements",
    )
    measurement_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date of measurement",
    )
    method = models.ForeignKey(
        Method,
        on_delete=models.RESTRICT,
        related_name="microxrf_measurements",
        blank=True,
        null=True,
        help_text="Method/Device used",
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"MicroXRF {self.sample} ({self.measurement_date})"


class MicroXRFElementMap(BaseModel):
    """Represents an element map from a MicroXRF measurement.

    Attributes:
        measurement (ForeignKey): Reference to MicroXRFMeasurement.
        element (CharField): Element or compound mapped.
        raster_file (FileField): Path to raster file (.tif).
        unit (CharField): Unit of measurement.
    """

    measurement = models.ForeignKey(
        MicroXRFMeasurement,
        on_delete=models.CASCADE,
        related_name="element_maps",
    )
    ELEMENT_CHOICES = [
        ("Al", "Aluminium (Al)"),
        ("As", "Arsenic (As)"),
        ("Ba", "Barium (Ba)"),
        ("Br", "Bromine (Br)"),
        ("C", "Carbon (C)"),
        ("Ca", "Calcium (Ca)"),
        ("Cl", "Chlorine (Cl)"),
        ("Co", "Cobalt (Co)"),
        ("Cr", "Chromium (Cr)"),
        ("Cu", "Copper (Cu)"),
        ("Fe", "Iron (Fe)"),
        ("Hg", "Mercury (Hg)"),
        ("K", "Potassium (K)"),
        ("Mg", "Magnesium (Mg)"),
        ("Mn", "Manganese (Mn)"),
        ("Mo", "Molybdenum (Mo)"),
        ("Na", "Sodium (Na)"),
        ("Ni", "Nickel (Ni)"),
        ("P", "Phosphorus (P)"),
        ("Pb", "Lead (Pb)"),
        ("S", "Sulfur (S)"),
        ("Se", "Selenium (Se)"),
        ("Si", "Silicon (Si)"),
        ("Sn", "Tin (Sn)"),
        ("Sr", "Strontium (Sr)"),
        ("Ti", "Titanium (Ti)"),
        ("V", "Vanadium (V)"),
        ("Zn", "Zinc (Zn)"),
        ("Zr", "Zirconium (Zr)"),
        ("Al2O3", "Aluminium Oxide (Al2O3)"),
        ("As2O3", "Arsenic Trioxide (As2O3)"),
        ("BaSO4", "Barium Sulfate (BaSO4)"),
        ("Br2", "Bromine (Br2)"),
        ("CaO", "Calcium Oxide (CaO)"),
        ("Cl2", "Chlorine (Cl2)"),
        ("CoO", "Cobalt(II) Oxide (CoO)"),
        ("Cr2O3", "Chromium(III) Oxide (Cr2O3)"),
        ("CuO", "Copper(II) Oxide (CuO)"),
        ("Fe2O3", "Iron(III) Oxide (Fe2O3)"),
        ("HgS", "Mercury Sulfide (HgS)"),
        ("K2O", "Potassium Oxide (K2O)"),
        ("MgO", "Magnesium Oxide (MgO)"),
        ("MoO3", "Molybdenum Trioxide (MoO3)"),
        ("Na2O", "Sodium Oxide (Na2O)"),
        ("NiO", "Nickel(II) Oxide (NiO)"),
        ("P2O5", "Phosphorus Pentoxide (P2O5)"),
        ("PbO", "Lead(II) Oxide (PbO)"),
        ("SeO2", "Selenium Dioxide (SeO2)"),
        ("SiO2", "Silicon Dioxide (SiO2)"),
        ("SnO2", "Tin(IV) Oxide (SnO2)"),
        ("SO3", "Sulfur Trioxide (SO3)"),
        ("SrSO4", "Strontium Sulfate (SrSO4)"),
        ("TiO2", "Titanium Dioxide (TiO2)"),
        ("VO2", "Vanadium Dioxide (VO2)"),
        ("ZnO", "Zinc Oxide (ZnO)"),
        ("ZrO2", "Zirconium Dioxide (ZrO2)"),
    ]
    element = models.CharField(
        max_length=10,
        help_text="Element (e.g. Fe, Mn, Si, ...)",
        choices=ELEMENT_CHOICES,
    )
    raster_file = models.FileField(
        upload_to="microxrf_raster/",
        help_text="Pfad zur .tif Rasterdatei",
    )
    unit = models.CharField(
        max_length=20,
        default="counts",
        help_text="Einheit (z.B. counts, ppm, %)",
    )

    def __str__(self):
        return f"{self.element} map ({self.measurement})"

    def get_raster_path(self):
        return os.path.join(settings.MEDIA_ROOT, self.raster_file.name)
