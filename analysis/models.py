"""Django models for the analysis app, covering geochronology, paleobotany, sedimentology, and geochemistry."""

from __future__ import annotations

import contextlib
import datetime
import json
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

    Args:
        name (CharField): Name of the algorithm.
        version (CharField): Version of the algorithm.
        description (TextField): Description of the algorithm.
        link (URLField): Link to the algorithm resource.
        file (FileField): File containing the algorithm.
        programming_language (CharField): Programming language used.
    """

    name = models.CharField(max_length=100)
    version = models.CharField(max_length=10)
    description = models.TextField(blank=True)
    link = models.URLField(blank=True)
    file = models.FileField(
        upload_to="analysis/algorithms/",
        blank=True,
        null=True,
    )
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

    def __str__(self) -> str:
        """Return the algorithm name."""
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
    description = models.TextField(blank=True)

    def filename(self) -> str | None:
        """Return the base filename of the uploaded file, or None if no file."""
        return Path(self.file.name).name if self.file else None

    def __str__(self) -> str:
        """Return a string combining device and creation timestamp."""
        return f"{self.device} - {self.created_at}"


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
    processing_description = models.TextField(blank=True)

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

    def processed_filename(self) -> str | None:
        """Return the base filename of the processed file, or None if no file."""
        return (
            Path(self.processed_file.name).name
            if self.processed_file
            else None
        )

    def __str__(self) -> str:
        """Return a human-readable label referencing the raw measurement."""
        return f"Processed data for {self.raw_measurement}"


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
        """Django metadata for Counting."""

        verbose_name = "Counting"
        verbose_name_plural = "Countings"

    def __str__(self) -> str:
        """Return the associated sample as a string."""
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
        """Django metadata for Pollen."""

        verbose_name = "Pollen"
        verbose_name_plural = "Pollen"

    def __str__(self) -> str:
        """Return the Latin name of the pollen species."""
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
        """Django metadata for PollenCount."""

        verbose_name = "Pollen Count"
        verbose_name_plural = "Pollen Counts"

    def __str__(self) -> str:
        """Return a label combining counting event and pollen species."""
        return f"{self.counting} - {self.pollen}"


# ======================
# GEOCHRONOLOGY MODELS
# ======================


def current_year() -> int:
    """Return the current calendar year in the Europe/Berlin timezone."""
    return datetime.datetime.now(tz=ZoneInfo("Europe/Berlin")).date().year


def max_value_current_year(value: int) -> None:
    """Validate that *value* does not exceed the current year."""
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
        verbose_name="Age [ka]",
        help_text="ka",
        blank=True,
        null=True,
    )

    age_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        verbose_name="Age error (1σ) [ka]",
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
        verbose_name="Palaeodose [Gy]",
        help_text="Gy",
        blank=True,
        null=True,
    )

    palaeodose_error = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Palaeodose error (1σ) [Gy]",
        help_text="Gy, 1σ",
        blank=True,
        null=True,
    )

    dose_rate = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        verbose_name="Dose rate [Gy/ka]",
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    dose_rate_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        verbose_name="Dose rate error (1σ) [Gy/ka]",
        help_text="Gy/ka, 1σ",
        blank=True,
        null=True,
    )

    published = models.BooleanField(
        default=False,
    )

    year_of_publication = models.PositiveIntegerField(
        default=current_year,
        validators=[
            MinValueValidator(1984),
            MaxValueValidator(current_year()),
        ],
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

    comments = models.TextField(blank=True)

    grain_size_min = models.IntegerField(
        verbose_name="Min. grain size [µm]",
        blank=True,
        null=True,
    )

    grain_size_max = models.IntegerField(
        verbose_name="Max. grain size [µm]",
        blank=True,
        null=True,
    )

    aliquot_size = models.CharField(
        max_length=30,
        blank=True,
    )

    aliquot_number_used_for_palaeodose = models.IntegerField(
        blank=True,
        null=True,
    )

    od_percent = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        verbose_name="OD [%]",
        help_text="%",
        blank=True,
        null=True,
    )

    od_percent_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        verbose_name="OD error (1σ) [%]",
        help_text="%",
        blank=True,
        null=True,
    )

    od_gy = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        verbose_name="OD [Gy]",
        help_text="Gy",
        blank=True,
        null=True,
    )

    od_gy_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        verbose_name="OD error (1σ) [Gy]",
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
        verbose_name="β source error [%]",
        blank=True,
        null=True,
    )

    uncertainty_beta_source_calibration = models.PositiveIntegerField(
        verbose_name="β calibration uncertainty [%]",
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
        verbose_name="g-value [%/dec]",
        help_text="%/dec",
        blank=True,
        null=True,
    )

    g_value_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        verbose_name="g-value error (1σ) [%/dec]",
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
        verbose_name="U [ppm]",
        help_text="ppm",
        blank=True,
        null=True,
    )

    u_ppm_error = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        verbose_name="U error (1σ) [ppm]",
        help_text="ppm",
        blank=True,
        null=True,
    )

    th_ppm = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="Th [ppm]",
        help_text="ppm",
        blank=True,
        null=True,
    )

    th_ppm_error = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        verbose_name="Th error (1σ) [ppm]",
        help_text="ppm",
        blank=True,
        null=True,
    )

    k_percent = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        verbose_name="K [%]",
        help_text="%",
        blank=True,
        null=True,
    )

    k_percent_error = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        verbose_name="K error (1σ) [%]",
        help_text="%",
        blank=True,
        null=True,
    )

    water_content_for_dating = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="Water content [%]",
        help_text="%",
        blank=True,
        null=True,
    )

    water_content_for_dating_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="Water content error (1σ) [%]",
        help_text="%",
        blank=True,
        null=True,
    )

    a_value = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="a-value",
        blank=True,
        null=True,
    )

    a_value_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="a-value error (1σ)",
        blank=True,
        null=True,
    )

    alpha_dose_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="α dose rate [Gy/ka]",
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    alpha_dose_rate_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="α dose rate error (1σ) [Gy/ka]",
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    beta_dose_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="β dose rate [Gy/ka]",
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    beta_dose_rate_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="β dose rate error (1σ) [Gy/ka]",
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    gamma_dose_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="γ dose rate [Gy/ka]",
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    gamma_dose_rate_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="γ dose rate error (1σ) [Gy/ka]",
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    cosmic_dose_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="Cosmic dose rate [Gy/ka]",
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    cosmic_dose_rate_error = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="Cosmic dose rate error (1σ) [Gy/ka]",
        help_text="Gy/ka",
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        """Return a label combining the laboratory ID and mineral type."""
        mineral_str = self.mineral or "Unknown"
        lab_id = (
            (self.laboratory_id or f"ID-{self.pk}")
            if self.pk
            else (self.laboratory_id or "Unsaved")
        )
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

    def __str__(self) -> str:
        """Return a label with lab ID and age."""
        age_str = f"{self.age} ka" if self.age is not None else "undated"
        return f"{self.lab_id} ({age_str})"


class CosmogenicNuclideDating(BaseModel):
    """Represents cosmogenic nuclide dating data for a sample."""

    NUCLIDE_CHOICES = [
        ("10Be", "¹⁰Be"),
        ("26Al", "²⁶Al"),
        ("36Cl", "³⁶Cl"),
        ("3He", "³He"),
        ("21Ne", "²¹Ne"),
        ("14C", "in-situ ¹⁴C"),
    ]
    MINERAL_CHOICES = [
        ("qtz", "Quartz"),
        ("fsp", "Feldspar"),
        ("px", "Pyroxene"),
        ("ol", "Olivine"),
        ("cc", "Calcite"),
        ("wr", "Whole rock"),
        ("other", "Other"),
    ]
    APPROACH_CHOICES = [
        ("exposure", "Exposure dating"),
        ("burial", "Burial dating"),
        ("denudation", "Denudation rate"),
    ]
    SCALING_CHOICES = [
        ("LSD", "LSD / Lifton-Sato-Dunai"),
        ("LSDn", "LSDn / Lifton-Sato-Dunai (updated)"),
        ("St", "St / Stone"),
        ("Lm", "Lm / Lal modified"),
        ("Du", "Du / Dunai"),
        ("De", "De / Desilets"),
    ]

    # --- Identification ---
    sample = models.ForeignKey(
        Sample,
        on_delete=models.RESTRICT,
        related_name="cosmogenic_nuclide_datings",
    )
    raw_data = models.ForeignKey(
        RawMeasurement,
        on_delete=models.RESTRICT,
        related_name="cosmogenic_nuclide_datings",
        blank=True,
        null=True,
    )
    lab_id = models.CharField(max_length=30, blank=True)
    nuclide = models.CharField(
        max_length=5,
        choices=NUCLIDE_CHOICES,
        blank=True,
    )
    mineral = models.CharField(
        max_length=10,
        choices=MINERAL_CHOICES,
        blank=True,
    )
    dating_approach = models.CharField(
        max_length=10,
        choices=APPROACH_CHOICES,
        blank=True,
    )

    # --- Concentration (published + standardized) ---
    # Concentrations are large integers (1e4–1e7 atoms/g); decimal_places=0
    nuclide_concentration = models.DecimalField(
        max_digits=14,
        decimal_places=0,
        blank=True,
        null=True,
        verbose_name="Published concentration [atoms/g]",
        help_text="As reported in publication (OCTOPUS: BE10NP / AL26NP)",
    )
    nuclide_concentration_error = models.DecimalField(
        max_digits=14,
        decimal_places=0,
        blank=True,
        null=True,
        verbose_name="Concentration error (1σ) [atoms/g]",
    )
    ams_standard = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="AMS standard",
        help_text="e.g. 07KNSTD, KNSTD, NIST_27900 (OCTOPUS: BESTND / ALSTND)",
    )
    normalized_concentration = models.DecimalField(
        max_digits=14,
        decimal_places=0,
        blank=True,
        null=True,
        verbose_name="Normalized concentration [atoms/g]",
        help_text="Standard-corrected for inter-lab comparison (OCTOPUS: BE10NC / AL26NC)",
    )
    normalized_concentration_error = models.DecimalField(
        max_digits=14,
        decimal_places=0,
        blank=True,
        null=True,
        verbose_name="Normalized concentration error (1σ) [atoms/g]",
    )

    # --- Age results ---
    exposure_age = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Exposure age [ka]",
    )
    exposure_age_error_internal = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Internal age error (1σ) [ka]",
        help_text="AMS measurement uncertainty only",
    )
    exposure_age_error_external = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="External age error (1σ) [ka]",
        help_text="Includes production rate uncertainty",
    )
    burial_age = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Burial age [ka]",
    )
    burial_age_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Burial age error (1σ) [ka]",
    )

    # --- Denudation rate ---
    # OCTOPUS distinguishes published (BE10EP) vs. CAIRN-recalculated (EBE_MMKYR).
    # We store only the published value; CAIRN-recalculated can be added later.
    denudation_rate = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Published denudation rate [mm/ka]",
        help_text="As reported in publication (OCTOPUS: BE10EP / AL26EP)",
    )
    denudation_rate_error = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Denudation rate error (1σ) [mm/ka]",
    )

    # --- Production rate & scaling ---
    scaling_method = models.CharField(
        max_length=10,
        choices=SCALING_CHOICES,
        blank=True,
    )
    calculation_software = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. CRONUS-Earth, CRONUScalc, CAIRN",
    )
    production_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name="Total production rate [atoms/g/a]",
    )
    production_rate_error = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name="Production rate error (1σ) [atoms/g/a]",
    )
    spallation_production_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name="Spallation production rate [atoms/g/a]",
    )
    muon_production_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name="Muon production rate [atoms/g/a]",
    )

    # --- Shielding (OCTOPUS: BETOPO, BESELF, BESNOW, BETOTS / ALTOPO, ALSELF, ALSNOW, ALTOTS) ---
    topographic_shielding = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name="Topographic shielding (0–1)",
    )
    self_shielding = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name="Self-shielding (0–1)",
    )
    snow_shielding = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name="Snow shielding (0–1)",
    )
    combined_shielding = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Combined shielding & scaling correction",
        help_text="Product of all shielding and production scaling factors (OCTOPUS: BETOTS / ALTOTS)",
    )
    erosion_rate_assumed = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Assumed erosion rate [mm/ka]",
        help_text="Steady-state erosion assumption for age calculation",
    )
    inheritance = models.DecimalField(
        max_digits=14,
        decimal_places=0,
        blank=True,
        null=True,
        verbose_name="Inheritance [atoms/g]",
    )

    # --- Error budget (OCTOPUS: ERRBE_AMS/MUON/PROD/TOT in g·cm⁻²·yr⁻¹) ---
    # Units are approach-dependent: g·cm⁻²·yr⁻¹ for denudation, ka for exposure age.
    error_ams = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="AMS measurement error",
    )
    error_muon = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Muon production error",
    )
    error_production_rate = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Production rate error",
    )
    error_total = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Total error (combined)",
        help_text="Quadrature sum of AMS + muon + production rate errors (OCTOPUS: ERRBE_TOT / ERRAL_TOT)",
    )

    # --- Publication ---
    published = models.BooleanField(default=False)
    year_of_publication = models.PositiveIntegerField(
        default=current_year,
        validators=[MinValueValidator(1984), max_value_current_year],
        blank=True,
        null=True,
    )
    thesis = models.CharField(
        max_length=4,
        choices=[
            ("BSc", "BSc"),
            ("MSc", "MSc"),
            ("PhD", "PhD"),
            ("None", "None"),
        ],
        default="None",
    )
    comments = models.TextField(blank=True)

    def __str__(self) -> str:
        """Return a label combining lab ID and nuclide."""
        lab_id = self.lab_id or (f"ID-{self.pk}" if self.pk else "Unsaved")
        nuclide_str = self.nuclide or "Unknown"
        return f"{lab_id} ({nuclide_str})"

    class Meta:
        """Django metadata for CosmogenicNuclideDating."""

        verbose_name = "Cosmogenic Nuclide Dating"
        verbose_name_plural = "Cosmogenic Nuclide Datings"


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


def default_classes() -> list:
    """Return a copy of the default Sympatec grain-size class boundaries."""
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

    def __str__(self) -> str:
        """Return the parameter name with its unit in brackets."""
        return f"{self.name} - [{self.unit}]"


class MeasurementSeries(BaseModel):
    """Represents a series of measurements.

    Attributes:
        datetime (DateTimeField): Date and time of the measurement series.
    """

    datetime = models.DateTimeField()

    def __str__(self) -> str:
        """Return a label with the series PK and datetime."""
        return f"Series {self.pk} – {self.datetime}"


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

    def __str__(self) -> str:
        """Return a label combining sample, method, and parameter."""
        return f"{self.sample} - {self.method} - {self.parameter}"


# Wentworth grain size class boundaries in µm (Wentworth 1922 / Folk & Ward)
_W_CLAY = 2
_W_FINE_SILT = 6.3
_W_MEDIUM_SILT = 20
_W_COARSE_SILT = 63
_W_FINE_SAND = 200
_W_MEDIUM_SAND = 630
_W_COARSE_SAND = 2000

# Ordered lookup: (upper boundary µm, field name). "gravel" has no upper bound.
_WENTWORTH_FRACTIONS: list[tuple[float, str]] = [
    (_W_CLAY, "clay"),
    (_W_FINE_SILT, "fine_silt"),
    (_W_MEDIUM_SILT, "medium_silt"),
    (_W_COARSE_SILT, "coarse_silt"),
    (_W_FINE_SAND, "fine_sand"),
    (_W_MEDIUM_SAND, "medium_sand"),
    (_W_COARSE_SAND, "coarse_sand"),
]

# Maps .mps file stat key → model field name
_STATS_KEY_MAP: dict[str, str] = {
    "Mean": "mean",
    "Mode": "mode",
    "Median": "median",
    "SD": "std",
    "Skew": "skew",
    "Kurtosis": "kurtosis",
    "FWMean": "fwmean",
    "FWMedian": "fwmedian",
    "FWSD": "fwsd",
    "FWSkew": "fwskew",
    "FWKurt": "fwkurt",
}


def _classify_fraction(class_value: float) -> str:
    """Return the Wentworth fraction name for a given grain size in µm."""
    for boundary, name in _WENTWORTH_FRACTIONS:
        if class_value < boundary:
            return name
    return "gravel"


def _parse_stats_line(line: str, stats: dict) -> None:
    """Parse one key=value line from a [SizeStats] block into the stats dict."""
    try:
        key, value = line.split("=")
        attr = _STATS_KEY_MAP.get(key.strip())
        if attr:
            stats[attr] = float(value.strip())
    except ValueError:
        pass


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
    gravel = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Gravel (≥ 2000 µm) [%]",
    )

    SOURCE_CHOICES = [
        ("file", "Imported from file"),
        ("manual", "Entered manually"),
    ]
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default="manual",
        editable=False,
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

    def _reclassify(
        self,
    ) -> tuple[float, float, float, float, float, float, float]:
        if isinstance(self.measured_data, str):
            self.measured_data = json.loads(self.measured_data)
        elif not isinstance(self.measured_data, list):
            msg = "Measured data must be a string or a list."
            raise TypeError(msg)

        fraction_names = [name for _, name in _WENTWORTH_FRACTIONS] + [
            "gravel",
        ]
        sums: dict[str, float] = dict.fromkeys(fraction_names, 0.0)

        for class_value, data_value in zip(
            self.classes,
            self.measured_data,
            strict=False,
        ):
            sums[_classify_fraction(class_value)] += data_value

        total = sum(self.measured_data)
        if total == 0:
            msg = "measured_data must not sum to zero."
            raise ValueError(msg)

        for attr, value in sums.items():
            setattr(self, attr, value / total * 100)

        return (
            self.fine_silt,
            self.medium_silt,
            self.coarse_silt,
            self.fine_sand,
            self.medium_sand,
            self.coarse_sand,
            self.clay,
        )

    def save(self, *args: object, **kwargs: object) -> None:
        """Recompute Wentworth fractions from raw data before saving."""
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

    def __str__(self) -> str:
        """Return a label combining sample identifier and measurement method."""
        return str(self.sample) + ", " + str(self.method)

    class Meta:
        """Django metadata for GrainSize."""

        verbose_name_plural = "Grain size"

    @staticmethod
    def _parse_block_line(line: str, block: str | None, state: dict) -> None:
        """Update mutable parse state for one data line based on the current block."""
        if block == "#Bindiam":
            with contextlib.suppress(ValueError):
                state["classes"].append(float(line))
        elif block == "#Binheight":
            with contextlib.suppress(ValueError):
                state["measured_data"].append(float(line))
        elif block in {"Size0", "Size1", "Size2"}:
            try:
                key, value = line.split("=")
                if key.strip() == "Obs":
                    state["concentration"].append(float(value.strip()))
            except ValueError:
                pass
        elif block == "SizeStats":
            _parse_stats_line(line, state["stats"])

    @classmethod
    def _parse_file_lines(cls, lines: list[str]) -> dict:
        """Parse .mps file lines into a structured data dict."""
        state: dict = {
            "classes": [],
            "measured_data": [],
            "concentration": [],
            "stats": dict.fromkeys(_STATS_KEY_MAP.values(), None),
        }
        current_block: str | None = None

        for raw_line in lines:
            line = raw_line.strip()
            if line.startswith("[") and line.endswith("]"):
                current_block = line[1:-1]
            else:
                cls._parse_block_line(line, current_block, state)

        return {
            "classes": state["classes"],
            "measured_data": state["measured_data"],
            "concentration": state["concentration"],
            **state["stats"],
        }

    @classmethod
    def from_file(
        cls,
        file_path: str | Path,
        sample: Sample,
        method: Method,
    ) -> Self:
        """Create a GrainSize instance by parsing a .mps instrument file."""
        with Path.open(file_path, encoding="latin-1", errors="ignore") as file:
            parsed = cls._parse_file_lines(file.readlines())

        try:
            sample_concentration = sum(parsed["concentration"]) / len(
                parsed["concentration"],
            )
        except (ZeroDivisionError, TypeError):
            msg = "No concentration data found in the file."
            raise ValueError(msg) from None

        return cls(
            sample=sample,
            method=method,
            classes=parsed["classes"],
            measured_data=parsed["measured_data"],
            sample_concentration=sample_concentration,
            **{k: parsed[k] for k in _STATS_KEY_MAP.values()},
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
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        """Return a label with sample and measurement date."""
        return f"MicroXRF {self.sample} ({self.measurement_date})"

    class Meta:
        """Django metadata for MicroXRFMeasurement."""

        verbose_name = "MicroXRF"
        verbose_name_plural = "MicroXRF"


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

    def __str__(self) -> str:
        """Return a label with element symbol and parent measurement."""
        return f"{self.element} map ({self.measurement})"

    def get_raster_path(self) -> Path:
        """Return the absolute filesystem path to the raster file."""
        return Path(settings.MEDIA_ROOT) / self.raster_file.name
