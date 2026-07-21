"""Integration tests for SampleAdmin's custom analysis sub-views.

Tests cover:
- All 18 URL names (6 models × changelist/add/change) resolve correctly
- Sample-scoped changelist returns 200 and is filtered to the sample
- Add form returns 200
- Unknown sample pk returns 404
- preserved_filters is set so the back-button points to the right URL
"""

from urllib.parse import parse_qs, unquote

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from field_data.models import Location, Sample
from prototype.models import Project

ANALYSIS_SLUGS = [
    "genericmeasurement",
    "grainsize",
    "luminescencedating",
    "radiocarbondating",
    "counting",
    "microxrfmeasurement",
    "cosmogenicnuclidedating",
]


class _AdminSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            "sa_admin", "sa@test.com", "pw"
        )
        cls.project = Project.objects.create(
            title="SA Test Project", label="SA01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="SA_LOC", data_source="internal", project=cls.project
        )
        cls.sample = Sample.objects.create(
            identifier="SA_S01", project=cls.project, location=cls.location
        )

    def setUp(self):
        self.client.force_login(self.superuser)


# ===========================================================================
# URL resolution — all 18 names must be resolvable
# ===========================================================================


class UrlRegistrationTest(_AdminSetup):

    def test_changelist_urls_resolve(self):
        for slug in ANALYSIS_SLUGS:
            with self.subTest(slug=slug):
                url = reverse(
                    f"admin:field_data_sample_{slug}", args=[self.sample.pk]
                )
                self.assertIn(
                    f"/field_data/sample/{self.sample.pk}/{slug}/", url
                )

    def test_add_urls_resolve(self):
        for slug in ANALYSIS_SLUGS:
            with self.subTest(slug=slug):
                url = reverse(
                    f"admin:field_data_sample_{slug}_add",
                    args=[self.sample.pk],
                )
                self.assertIn(
                    f"/field_data/sample/{self.sample.pk}/{slug}/add/", url
                )

    def test_change_urls_resolve(self):
        for slug in ANALYSIS_SLUGS:
            with self.subTest(slug=slug):
                url = reverse(
                    f"admin:field_data_sample_{slug}_change",
                    args=[self.sample.pk, 99],
                )
                self.assertIn(
                    f"/field_data/sample/{self.sample.pk}/{slug}/99/change/",
                    url,
                )


# ===========================================================================
# Changelist view
# ===========================================================================


class ChangelistViewTest(_AdminSetup):

    def test_returns_200(self):
        url = reverse(
            "admin:field_data_sample_genericmeasurement", args=[self.sample.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_filtered_to_sample(self):
        url = reverse(
            "admin:field_data_sample_genericmeasurement", args=[self.sample.pk]
        )
        response = self.client.get(url)
        assert response.context_data is not None
        cl = response.context_data["cl"]
        self.assertEqual(
            cl.params.get("sample__id__exact"), str(self.sample.pk)
        )

    def test_preserved_filters_points_back_to_sample(self):
        """preserved_filters must encode sample__id__exact so the back-button works."""
        url = reverse(
            "admin:field_data_sample_genericmeasurement", args=[self.sample.pk]
        )
        response = self.client.get(url)
        assert response.context_data is not None
        pf = response.context_data.get("preserved_filters", "")
        decoded = unquote(pf)
        self.assertIn(f"sample__id__exact={self.sample.pk}", decoded)

    def test_unknown_sample_returns_404(self):
        url = reverse(
            "admin:field_data_sample_genericmeasurement", args=[999999]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# ===========================================================================
# Add view
# ===========================================================================


class AddViewTest(_AdminSetup):

    def test_returns_200(self):
        url = reverse(
            "admin:field_data_sample_genericmeasurement_add",
            args=[self.sample.pk],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_unknown_sample_returns_404(self):
        url = reverse(
            "admin:field_data_sample_genericmeasurement_add", args=[999999]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# ===========================================================================
# Changelist query count — regression test for N+1 on project/location
# ===========================================================================


class SampleChangelistQueryCountTest(_AdminSetup):
    """SampleAdmin's changelist must select_related() project and location.

    Without it, the "project" and "location" list_display columns each
    trigger one extra query per row, so the query count grows linearly with
    the number of samples shown on the page.
    """

    def test_query_count_does_not_scale_with_row_count(self):
        url = reverse("admin:field_data_sample_changelist")

        with CaptureQueriesContext(connection) as baseline:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        baseline_count = len(baseline.captured_queries)

        for i in range(20):
            Sample.objects.create(
                identifier=f"SA_EXTRA_{i:03d}",
                project=self.project,
                location=self.location,
            )

        with CaptureQueriesContext(connection) as after:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            len(after.captured_queries),
            baseline_count,
            "Query count grew with the number of samples — project/location "
            "must stay select_related() on SampleAdmin.get_queryset().",
        )


# ===========================================================================
# FieldPhoto inline on Location and Layer change pages
# ===========================================================================


class FieldPhotoInlineTest(_AdminSetup):
    """The FieldPhoto generic inline must render on Location and Layer forms."""

    def test_location_change_page_shows_photo_inline(self):
        url = reverse(
            "admin:field_data_location_change", args=[self.location.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field_data-fieldphoto")

    def test_layer_change_page_shows_photo_inline(self):
        from field_data.models import Layer

        layer = Layer.objects.create(location=self.location, identifier=1)
        url = reverse("admin:field_data_layer_change", args=[layer.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field_data-fieldphoto")
