"""Dagster repository - entry point for assets and jobs."""

import os

import django
from dagster import Definitions, load_assets_from_modules

from . import assets, jobs
from .maintenance_jobs import (
    backup_job,
    duckdb_export_job,
    integrity_check_job,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prototype.settings")
django.setup()


all_assets = load_assets_from_modules([assets])


def get_dagster_resources() -> dict:
    """Dagster resources from Django settings."""
    return {}


defs = Definitions(
    assets=all_assets,
    jobs=[
        jobs.full_pipeline_job,
        jobs.data_quality_job,
        jobs.extraction_job,
        backup_job,
        duckdb_export_job,
        integrity_check_job,
    ],
    resources=get_dagster_resources(),
    # schedules=[jobs.daily_pipeline_schedule],
)
