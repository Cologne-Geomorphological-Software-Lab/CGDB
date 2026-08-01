"""Tests for the run-status sensors that sync MaintenanceRun with Dagster."""

from unittest.mock import MagicMock

import pytest

from orchestration.dagster_home.sensors import (
    _sync_maintenance_run,
    maintenance_run_failure_sensor,
    maintenance_run_success_sensor,
)
from orchestration.models import MaintenanceRun


def _make_context(tags: dict) -> MagicMock:
    context = MagicMock()
    context.dagster_run.tags = tags
    context.dagster_run.run_id = "fake-dagster-run-id"
    return context


@pytest.mark.django_db
class TestSyncMaintenanceRun:
    def test_sets_status_and_finished_at(self):
        run = MaintenanceRun.objects.create(job_type="backup", status="running")
        context = _make_context({"maintenance_run_id": str(run.pk)})

        _sync_maintenance_run(context, status="success")

        run.refresh_from_db()
        assert run.status == "success"
        assert run.finished_at is not None

    def test_sets_failed_status(self):
        run = MaintenanceRun.objects.create(job_type="backup", status="running")
        context = _make_context({"maintenance_run_id": str(run.pk)})

        _sync_maintenance_run(context, status="failed")

        run.refresh_from_db()
        assert run.status == "failed"

    def test_missing_tag_is_a_noop(self):
        """A Dagster run not tagged with maintenance_run_id (e.g. the asset-based
        pipeline jobs) must not raise or touch any MaintenanceRun."""
        context = _make_context({})
        _sync_maintenance_run(context, status="success")  # must not raise

    def test_unknown_run_id_logs_warning_not_raise(self):
        context = _make_context({"maintenance_run_id": "999999"})
        _sync_maintenance_run(context, status="success")  # must not raise
        context.log.warning.assert_called_once()


class TestRunStatusSensorRegistration:
    """The sensors themselves are thin @run_status_sensor wrappers around
    _sync_maintenance_run (covered above) — Dagster's own event-routing
    machinery is not re-tested here, only that each sensor is active by
    default (the one property that's easy to silently get wrong and would
    make the whole audit-trail sync a no-op)."""

    def test_sensors_default_to_running(self):
        """DefaultSensorStatus.STOPPED (Dagster's decorator default) would
        silently disable the audit-trail sync until someone manually flips
        it on in the Dagster UI — both sensors must override this."""
        from dagster import DefaultSensorStatus

        assert (
            maintenance_run_success_sensor.default_status
            == DefaultSensorStatus.RUNNING
        )
        assert (
            maintenance_run_failure_sensor.default_status
            == DefaultSensorStatus.RUNNING
        )
