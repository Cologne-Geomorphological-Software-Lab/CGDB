"""Models for tracking maintenance job runs and DuckDB export configuration."""

from django.contrib.auth.models import User
from django.db import models

from prototype.models import BaseModel


class MaintenanceRun(BaseModel):
    """Tracks a single execution of a scheduled maintenance job."""

    JOB_TYPES = [
        ("backup", "Backup"),
        ("duckdb", "DuckDB Export"),
        ("integrity", "Integrity Check"),
    ]
    STATUSES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]
    DUMP_FORMATS = [
        ("custom", "Custom (pg_dump -Fc, compressed — recommended)"),
        ("plain", "Plain SQL (pg_dump -Fp, human-readable)"),
    ]

    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    status = models.CharField(
        max_length=20, choices=STATUSES, default="pending"
    )
    dump_format = models.CharField(
        max_length=10,
        choices=DUMP_FORMATS,
        default="custom",
        help_text="Output format for backup jobs (ignored for other job types).",
    )
    triggered_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    result_file = models.FileField(
        upload_to="maintenance/", null=True, blank=True
    )
    log = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        """Meta options for MaintenanceRun."""

        verbose_name = "Maintenance Run"
        verbose_name_plural = "Maintenance Runs"

    def __str__(self) -> str:
        """Return a human-readable representation of this run."""
        return (
            f"{self.get_job_type_display()} [{self.status}]"
            f" @ {self.started_at or 'pending'}"
        )


class DuckDBTableConfig(BaseModel):
    """Configuration controlling which Django models are exported to DuckDB."""

    ROLES = [
        ("fact", "Fact"),
        ("dim", "Dimension"),
        ("exclude", "Exclude"),
    ]

    app_label = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=ROLES, default="dim")
    include_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Fields to include (empty = all fields).",
    )
    exclude_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Fields to exclude from export.",
    )

    class Meta(BaseModel.Meta):
        """Meta options for DuckDBTableConfig."""

        unique_together = ("app_label", "model_name")
        verbose_name = "DuckDB Table Config"
        verbose_name_plural = "DuckDB Table Configs"

    def __str__(self) -> str:
        """Return a human-readable representation of this config."""
        return f"{self.app_label}.{self.model_name} ({self.role})"
