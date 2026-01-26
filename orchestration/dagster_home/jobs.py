"""Dagster jobs - orchestrate asset execution."""

from dagster import AssetSelection, define_asset_job

full_pipeline_job = define_asset_job(
    name="full_pipeline",
    description="Complete ETL pipeline",
    selection=AssetSelection.all(),
)

data_quality_job = define_asset_job(
    name="data_quality_check",
    description="Data quality validation",
    selection=AssetSelection.groups("data_quality"),
)

extraction_job = define_asset_job(
    name="extract_data",
    description="Extract from Django database",
    selection=AssetSelection.groups("django_extraction"),
)

# Uncomment for scheduled execution
"""
daily_pipeline_schedule = ScheduleDefinition(
    job=full_pipeline_job,
    cron_schedule="0 2 * * *",
    description="Daily pipeline run"
)
"""
