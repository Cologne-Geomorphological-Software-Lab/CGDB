"""Admin-layer integration tests (tech debt A14).

Both GrainSizeAdmin's .$av file-upload path (save_model/process_file) and
MicroXRFElementInline's thumbnail renderer (preview()) previously had only
their underlying pure functions tested (GrainSize.from_file() in
test_grainsize_fromfile.py) - never exercised through the actual admin
request/render path. These tests close that gap: a real POST through the
admin add view for GrainSize, and a real small TIFF through preview() for
MicroXRF.
"""

import io

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from PIL import Image

from analysis.admin import MicroXRFElementInline
from analysis.models import GrainSize, MicroXRFElementMap, MicroXRFMeasurement
from analysis.tests._mps_fixtures import MINIMAL_AV
from field_data.models import Location, Sample
from laboratory.models import Method
from prototype.models import Project


class GrainSizeAdminUploadTest(TestCase):
    """POST a real .$av file through the admin add view."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            "gs_admin", "gs_admin@test.com", "pw"
        )
        cls.project = Project.objects.create(
            title="GS Admin Project", label="GSA01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="GSA_LOC", data_source="internal", project=cls.project
        )
        cls.sample = Sample.objects.create(
            identifier="GSA_S01", project=cls.project, location=cls.location
        )
        cls.method = Method.objects.create(
            name="GSA Method", category="CHEM"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_upload_populates_fields_and_marks_source_file(self):
        upload = SimpleUploadedFile(
            "sample.$av",
            MINIMAL_AV.encode("latin-1"),
            content_type="application/octet-stream",
        )
        url = reverse("admin:analysis_grainsize_add")
        response = self.client.post(
            url,
            data={
                "sample": self.sample.pk,
                "method": "L",
                "file": upload,
                "_save": "Save",
            },
        )
        self.assertEqual(
            response.status_code,
            302,
            getattr(response, "context", {}) and response.context.get("errors"),
        )

        gs = GrainSize.objects.get(sample=self.sample)
        self.assertEqual(gs.source, "file")
        self.assertEqual(gs.classes, [10.0, 20.0])
        self.assertEqual(gs.mean, 15.0)
        self.assertEqual(gs.median, 14.0)
        self.assertEqual(gs.fwkurt, 2.9)


class MicroXRFPreviewTest(TestCase):
    """Render preview() against a small, real TIFF."""

    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            title="XRF Preview Project", label="XPP01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="XPP_LOC", data_source="internal", project=cls.project
        )
        cls.sample = Sample.objects.create(
            identifier="XPP_S01", project=cls.project, location=cls.location
        )
        cls.measurement = MicroXRFMeasurement.objects.create(sample=cls.sample)

    def _make_element_map(self, image_mode: str) -> MicroXRFElementMap:
        img = Image.new(image_mode, (8, 8))
        buf = io.BytesIO()
        img.save(buf, format="TIFF")
        buf.seek(0)
        return MicroXRFElementMap.objects.create(
            measurement=self.measurement,
            element="Fe",
            raster_file=SimpleUploadedFile(
                "element.tif", buf.read(), content_type="image/tiff"
            ),
        )

    def test_preview_renders_rgb_tiff_as_inline_image(self):
        obj = self._make_element_map("RGB")
        result = MicroXRFElementInline(
            MicroXRFMeasurement, django_admin.site
        ).preview(obj)
        self.assertIn("<img", result)
        self.assertIn("data:image/png;base64,", result)

    def test_preview_renders_float_mode_tiff_via_normalization(self):
        """Float-mode ("F") TIFFs go through _normalize_float_image() first."""
        obj = self._make_element_map("F")
        result = MicroXRFElementInline(
            MicroXRFMeasurement, django_admin.site
        ).preview(obj)
        self.assertIn("<img", result)

    def test_preview_returns_placeholder_when_no_file(self):
        obj = MicroXRFElementMap(
            measurement=self.measurement, element="Fe", raster_file=""
        )
        result = MicroXRFElementInline(
            MicroXRFMeasurement, django_admin.site
        ).preview(obj)
        self.assertEqual(result, "No preview")

    def test_preview_logs_and_hides_details_for_corrupt_file(self):
        """tech debt A18: a malformed raster must not fail silently from an
        ops perspective, and the raw exception text must not leak into the
        rendered admin page."""
        obj = MicroXRFElementMap.objects.create(
            measurement=self.measurement,
            element="Fe",
            raster_file=SimpleUploadedFile(
                "corrupt.tif", b"not a real tiff", content_type="image/tiff"
            ),
        )
        with self.assertLogs("analysis.admin", level="WARNING") as cm:
            result = MicroXRFElementInline(
                MicroXRFMeasurement, django_admin.site
            ).preview(obj)
        self.assertEqual(
            result, "Preview unavailable — see server logs for details."
        )
        self.assertIn(str(obj.pk), cm.output[0])
