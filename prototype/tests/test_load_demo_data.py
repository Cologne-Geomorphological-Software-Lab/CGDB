"""Tests for the load_demo_data command (prototype/demo_data.py).

The Docker demo runs the command on every container start, so it must be
idempotent and must leave the demo accounts able to see the demo project.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings

from analysis.models import GrainSize
from field_data.models import Location, Sample
from geodata.models import Landform
from prototype.access import has_model_perm, has_project_perm
from prototype.demo_data import LANDFORM_SOURCE, PI_USERNAME, PROJECT_LABEL, VIEWER_USERNAME, demo_counts
from prototype.models import Project


def _load(*args: str) -> str:
    out = StringIO()
    call_command("load_demo_data", *args, stdout=out)
    return out.getvalue()


@override_settings(DEBUG=True)
class LoadDemoDataTest(TestCase):
    def test_creates_data_in_every_category(self):
        _load()
        counts = demo_counts()
        self.assertEqual(counts["locations"], 8)
        self.assertEqual(counts["samples"], 24)
        for kind, n in counts.items():
            self.assertGreater(n, 0, msg=kind)

    def test_second_run_adds_nothing(self):
        _load()
        before = demo_counts()
        output = _load()
        self.assertEqual(demo_counts(), before)
        self.assertIn("already present", output)
        self.assertEqual(Project.objects.filter(label=PROJECT_LABEL).count(), 1)
        self.assertEqual(Location.objects.filter(data_source="literature").count(), 1)

    def test_pi_can_edit_and_viewer_can_view_the_project(self):
        _load()
        users = User.objects
        project = Project.objects.get(label=PROJECT_LABEL)
        pi = users.get(username=PI_USERNAME)
        viewer = users.get(username=VIEWER_USERNAME)

        self.assertTrue(pi.is_staff)
        self.assertTrue(has_project_perm(pi, "change", project))
        self.assertTrue(has_model_perm(pi, "change", Sample))
        self.assertTrue(has_project_perm(viewer, "view", project))
        self.assertFalse(has_model_perm(viewer, "change", Sample))
        self.assertTrue(has_model_perm(viewer, "view", Landform))

    def test_password_option_is_applied(self):
        _load("--password", "s3cret-demo")
        pi = User.objects.get(username=PI_USERNAME)
        self.assertTrue(pi.check_password("s3cret-demo"))

    def test_grain_size_fractions_sum_to_100(self):
        _load()
        fractions = ("clay", "fine_silt", "medium_silt", "coarse_silt", "fine_sand", "medium_sand", "coarse_sand", "gravel")
        for gs in GrainSize.objects.filter(sample__project__label=PROJECT_LABEL):
            total = sum(getattr(gs, f) or 0 for f in fractions)
            self.assertAlmostEqual(total, 100.0, delta=0.5)

    def test_reset_removes_demo_data_and_recreates_it(self):
        _load()
        call_command("load_demo_data", "--reset", stdout=StringIO())
        self.assertEqual(demo_counts()["samples"], 24)
        self.assertEqual(Landform.objects.filter(source=LANDFORM_SOURCE).count(), 6)
        self.assertEqual(User.objects.filter(username=PI_USERNAME).count(), 1)


@pytest.mark.postgis_only
@override_settings(DEBUG=True)
class DemoLandformTileTest(TestCase):
    """The demo map shows landforms only through PostGIS vector tiles."""

    def test_demo_user_gets_a_tile_with_demo_landforms(self):
        _load("--password", "pw")
        client = Client()
        client.login(username=PI_USERNAME, password="pw")
        # z=2 tile over Europe, which contains the Europe demo region.
        resp = client.get("/api/v1/landforms/tiles/2/2/1.mvt")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/x-protobuf")
        self.assertGreater(len(resp.content), 0)


@override_settings(DEBUG=False)
class LoadDemoDataSafetyTest(TestCase):
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            _load()
        self.assertFalse(Project.objects.filter(label=PROJECT_LABEL).exists())

    def test_runs_without_debug_when_allowed(self):
        _load("--allow-without-debug")
        self.assertTrue(Project.objects.filter(label=PROJECT_LABEL).exists())
