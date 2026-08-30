"""Dagster repository - entry point for jobs and sensors."""

import os

import django
from dagster import Definitions

from .maintenance_jobs import (
    backup_job,
    duckdb_export_job,
    integrity_check_job,
)
from .sensors import (
    maintenance_run_failure_sensor,
    maintenance_run_success_sensor,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prototype.settings")
django.setup()


defs = Definitions(
    jobs=[
        backup_job,
        duckdb_export_job,
        integrity_check_job,
    ],
    sensors=[maintenance_run_success_sensor, maintenance_run_failure_sensor],
)
