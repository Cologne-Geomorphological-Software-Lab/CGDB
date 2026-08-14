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

from field_data.admin import SiteAdmin
from field_data.models import (
    Country,
    Location,
    Province,
    Sample,
    Site,
    StudyArea,
    Transect,
)
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


# ===========================================================================
# GIS map widgets (Phase 5: StudyArea/Transect/Country/Province admin cleanup)
# ===========================================================================

# django.contrib.gis's OpenLayersWidget template (gis/openlayers.html) always
# renders this wrapper div around the map — a plain textarea-only form (the
# pre-Phase-5 state) never contains it.
_GIS_WIDGET_MARKER = "dj_map_wrapper"


class GISWidgetChangeFormTest(_AdminSetup):
    """StudyArea/Transect/Country/Province change forms must render a map widget."""

    def test_study_area_change_form_has_map_widget(self):
        study_area = StudyArea.objects.create(
            label="Test Area", project=self.project
        )
        url = reverse(
            "admin:field_data_studyarea_change", args=[study_area.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _GIS_WIDGET_MARKER)

    def test_transect_change_form_has_map_widget_and_multiline_field(self):
        study_area = StudyArea.objects.create(
            label="Test Area", project=self.project
        )
        transect = Transect.objects.create(
            identifier="T1", study_area=study_area, description="desc"
        )
        url = reverse("admin:field_data_transect_change", args=[transect.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _GIS_WIDGET_MARKER)
        # multiline was previously absent from admin.py entirely (no
        # fieldsets at all) — confirm it's now a reachable form field.
        self.assertContains(response, 'name="multiline"')

    def test_country_change_form_has_map_widget(self):
        country = Country.objects.create(name="Testland", iso_code="TST")
        url = reverse("admin:field_data_country_change", args=[country.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _GIS_WIDGET_MARKER)

    def test_province_change_form_has_map_widget(self):
        country = Country.objects.create(name="Testland", iso_code="TST")
        province = Province.objects.create(name="Testprovince", country=country)
        url = reverse("admin:field_data_province_change", args=[province.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _GIS_WIDGET_MARKER)


class SiteAdminNoGeoMixinTest(_AdminSetup):
    """Site has no geometry field — SiteAdmin's GIS mixin was dead code."""

    def test_site_admin_does_not_mix_in_geo_admin(self):
        mro_names = [cls.__name__ for cls in SiteAdmin.__mro__]
        self.assertNotIn("GeoModelAdminMixin", mro_names)

    def test_site_change_form_renders(self):
        study_area = StudyArea.objects.create(
            label="Test Area", project=self.project
        )
        site = Site.objects.create(label="Test Site", study_area=study_area)
        url = reverse("admin:field_data_site_change", args=[site.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# LocationAdmin.map_preview — ported from CDN OpenLayers/proj4 to the Vite bundle
# ===========================================================================


class LocationMapPreviewTest(_AdminSetup):
    """map_preview must use the bundled frontend, not CDN script tags."""

    def test_change_form_uses_vite_bundle_not_cdn(self):
        # .location is recomputed from easting/northing/srid on save() — it
        # cannot be set directly (see field_data/models.py Location.save()).
        self.location.easting = 7.0
        self.location.northing = 50.0
        self.location.srid = 4326
        self.location.save()
        url = reverse(
            "admin:field_data_location_change", args=[self.location.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cgdb-loc-preview")
        self.assertContains(response, "adminLocationPreview")
        self.assertNotContains(response, "cdn.jsdelivr.net")
        self.assertNotContains(response, "cdnjs.cloudflare.com")


class ProvinceChangelistQueryCountTest(_AdminSetup):
    """ProvinceAdmin's changelist must select_related('country').

    Without it, the "country" list_display column triggers one extra query
    per row, so the query count grows linearly with the number of provinces
    shown on the page.
    """

    def test_query_count_does_not_scale_with_row_count(self):
        country = Country.objects.create(name="Testland", iso_code="TST")
        url = reverse("admin:field_data_province_changelist")

        with CaptureQueriesContext(connection) as baseline:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        baseline_count = len(baseline.captured_queries)

        for i in range(20):
            Province.objects.create(
                name=f"Province {i:03d}", country=country
            )

        with CaptureQueriesContext(connection) as after:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            len(after.captured_queries),
            baseline_count,
            "Query count grew with the number of provinces — country must "
            "stay select_related() on ProvinceAdmin.get_queryset().",
        )


# ===========================================================================
# FieldPhotoAdmin.download_file — protected download route (tech debt FD8)
# ===========================================================================


class FieldPhotoDownloadViewTests(TestCase):
    """FieldPhoto.file must be reachable only by users who can view the
    owning project, matching every other project-scoped resource in this
    app -- not via the raw, unauthenticated-in-production media URL."""

    @classmethod
    def setUpTestData(cls):
        from guardian.shortcuts import assign_perm

        from field_data.models import FieldPhoto

        cls.member = User.objects.create_user(
            username="fp_member", password="pw", is_staff=True
        )
        cls.non_member = User.objects.create_user(
            username="fp_non_member", password="pw", is_staff=True
        )
        cls.superuser = User.objects.create_superuser(
            "fp_super", "fps@test.com", "pw"
        )
        cls.project = Project.objects.create(
            title="FieldPhoto Project", label="FP01", status="ACTIVE"
        )
        assign_perm("view_project", cls.member, cls.project)
        cls.location = Location.objects.create(
            identifier="FP_LOC", data_source="internal", project=cls.project
        )

    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from field_data.models import FieldPhoto

        self._FieldPhoto = FieldPhoto
        self.photo = FieldPhoto.objects.create(content_object=self.location)
        self.photo.file.save(
            "profile.jpg", SimpleUploadedFile("profile.jpg", b"photo-bytes")
        )
        self.addCleanup(lambda: self.photo.file.delete(save=False))
        self.url = reverse(
            "admin:field_data_fieldphoto_download", args=[self.photo.pk]
        )

    def test_project_member_can_download(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            b"".join(response.streaming_content), b"photo-bytes"
        )

    def test_non_member_gets_404_not_the_file(self):
        self.client.force_login(self.non_member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cannot_download(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403, 404))

    def test_superuser_can_download_regardless_of_membership(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Fully consume the streaming response so the underlying file handle
        # is released before this test's addCleanup tries to delete it
        # (Windows keeps an open file locked against deletion).
        b"".join(response.streaming_content)

    def test_404_when_photo_has_no_file(self):
        empty_photo = self._FieldPhoto.objects.create(
            content_object=self.location
        )
        url = reverse(
            "admin:field_data_fieldphoto_download", args=[empty_photo.pk]
        )
        self.client.force_login(self.member)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_404_for_nonexistent_photo(self):
        url = reverse("admin:field_data_fieldphoto_download", args=[999999])
        self.client.force_login(self.member)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_hidden_from_admin_index(self):
        """FieldPhotoAdmin exists only to host the download route."""
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:index"))
        self.assertNotContains(response, "field_data/fieldphoto/")


class FieldPhotoWidgetLinksToProtectedViewTests(TestCase):
    """The inline's file widget must render the protected download URL,
    not the FieldFile's raw (in production, unauthenticated) .url."""

    @classmethod
    def setUpTestData(cls):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from field_data.models import FieldPhoto

        cls.superuser = User.objects.create_superuser(
            "fpw_super", "fpws@test.com", "pw"
        )
        cls.project = Project.objects.create(
            title="FieldPhoto Widget Project", label="FPW01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="FPW_LOC", data_source="internal", project=cls.project
        )
        cls.photo = FieldPhoto.objects.create(content_object=cls.location)
        cls.photo.file.save(
            "sketch.jpg", SimpleUploadedFile("sketch.jpg", b"sketch-bytes")
        )

    @classmethod
    def tearDownClass(cls):
        cls.photo.file.delete(save=False)
        super().tearDownClass()

    def test_location_change_form_links_to_protected_download_not_raw_url(
        self,
    ):
        self.client.force_login(self.superuser)
        url = reverse(
            "admin:field_data_location_change", args=[self.location.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        protected_url = reverse(
            "admin:field_data_fieldphoto_download", args=[self.photo.pk]
        )
        content = response.content.decode()
        self.assertIn(protected_url, content)
        self.assertNotIn(self.photo.file.url, content)
