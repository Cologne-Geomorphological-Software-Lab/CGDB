"""Dagster repository - entry point for assets and jobs."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prototype.settings")
django.setup()

from dagster import Definitions, load_assets_from_modules
from django.conf import settings

from . import assets, jobs

all_assets = load_assets_from_modules([assets])


def get_dagster_resources():
    """Dagster resources from Django settings."""
    return {}


defs = Definitions(
    assets=all_assets,
    jobs=[
        jobs.full_pipeline_job,
        jobs.data_quality_job,
        jobs.extraction_job,
    ],
    resources=get_dagster_resources(),
    # schedules=[jobs.daily_pipeline_schedule],
)
