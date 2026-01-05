"""Dagster assets - ETL pipeline example."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prototype.settings")
django.setup()

from dagster import AssetExecutionContext, asset
from django.apps import apps


@asset(description="Extract from Django models", group_name="django_extraction")
def extract_sample_data(context: AssetExecutionContext) -> dict:
    """Extract sample data from Django database."""
    try:
        Sample = apps.get_model("field_data", "Sample")
        sample_count = Sample.objects.count()
        context.log.info(f"Extracted {sample_count} samples")
        return {"total_samples": sample_count, "status": "success"}
    except Exception as e:
        context.log.error(f"Extraction failed: {e}")
        return {"status": "error", "message": str(e)}


@asset(
    description="Data quality validation",
    group_name="data_quality",
    deps=[extract_sample_data],
)
def validate_sample_data(
    context: AssetExecutionContext, extract_sample_data: dict
) -> dict:
    """Validate extracted data quality."""
    passed = extract_sample_data.get("status") == "success"
    context.log.info(f"Quality check {'passed' if passed else 'failed'}")
    return {
        "validation": "passed" if passed else "failed",
        "details": extract_sample_data,
    }


@asset(
    description="Transform for OLAP",
    group_name="transformation",
    deps=[validate_sample_data],
)
def transform_to_duckdb(context: AssetExecutionContext) -> dict:
    """Transform and load data into DuckDB."""
    context.log.info("DuckDB integration - implement for your OLAP schema")
    return {"status": "blueprint", "message": "Implement DuckDB integration"}
