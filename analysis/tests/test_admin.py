"""Integration tests for SampleContextMixin in analysis/admin.py.

Tests cover the redirect logic that keeps all measurement forms under the
Sample URL hierarchy:
- changelist_view: redirects when sample__id__exact is in GET (GET only)
- add_view: redirects when sample is in GET (GET only, not POST)
- change_view: redirects when obj has sample_id (GET only, not POST)
- get_changeform_initial_data: pre-fills sample FK from preserved_filters
"""

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from analysis.models import GenericMeasurement, Parameter
from field_data.models import Location, Sample
from laboratory.models import Method
from prototype.models import Project, Researcher


class _AdminSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            "scm_admin", "scm@test.com", "pw"
        )
        cls.project = Project.objects.create(
            title="SCM Test Project", label="SCM01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="SCM_LOC", data_source="internal", project=cls.project
        )
        cls.sample = Sample.objects.create(
            identifier="SCM_S01", project=cls.project, location=cls.location
        )
        cls.method = Method.objects.create(name="SCM Method", category="CHEM")
        cls.parameter = Parameter.objects.create(
            name="Silicon", token="Si", unit="mg/kg"
        )

    def setUp(self):
        self.client.force_login(self.superuser)


# ===========================================================================
# changelist_view redirect
# ===========================================================================


class ChangelistRedirectTest(_AdminSetup):

    def test_redirects_to_sample_scoped_url(self):
        url = reverse("admin:analysis_genericmeasurement_changelist")
        response = self.client.get(url, {"sample__id__exact": self.sample.pk})
        expected = reverse(
            "admin:field_data_sample_genericmeasurement", args=[self.sample.pk]
        )
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    def test_no_redirect_without_sample_param(self):
        url = reverse("admin:analysis_genericmeasurement_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_no_redirect_when_already_sample_scoped(self):
        url = reverse(
            "admin:field_data_sample_genericmeasurement", args=[self.sample.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# add_view redirect — GET only, not POST
# ===========================================================================


class AddViewRedirectTest(_AdminSetup):

    def test_get_redirects_to_sample_scoped_add_url(self):
        url = reverse("admin:analysis_genericmeasurement_add")
        response = self.client.get(url, {"sample": self.sample.pk})
        expected = reverse(
            "admin:field_data_sample_genericmeasurement_add",
            args=[self.sample.pk],
        )
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    def test_post_does_not_redirect_to_sample_scoped_url(self):
        """POST with ?sample= must NOT redirect — form data would be discarded."""
        url = reverse("admin:analysis_genericmeasurement_add")
        sample_scoped_add = reverse(
            "admin:field_data_sample_genericmeasurement_add",
            args=[self.sample.pk],
        )
        response = self.client.post(f"{url}?sample={self.sample.pk}", data={})
        self.assertNotEqual(response.get("Location"), sample_scoped_add)

    def test_get_via_changelist_filters_redirects(self):
        from urllib.parse import urlencode

        cl_filters = urlencode(
            {"_changelist_filters": f"sample__id__exact={self.sample.pk}"}
        )
        url = reverse("admin:analysis_genericmeasurement_add")
        response = self.client.get(f"{url}?{cl_filters}")
        expected = reverse(
            "admin:field_data_sample_genericmeasurement_add",
            args=[self.sample.pk],
        )
        self.assertRedirects(response, expected, fetch_redirect_response=False)


# ===========================================================================
# change_view redirect — GET only, not POST
# ===========================================================================


class ChangeViewRedirectTest(_AdminSetup):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.measurement = GenericMeasurement.objects.create(
            sample=cls.sample,
            method=cls.method,
            parameter=cls.parameter,
            value=42.0,
        )

    def test_get_redirects_to_sample_scoped_change_url(self):
        url = reverse(
            "admin:analysis_genericmeasurement_change",
            args=[self.measurement.pk],
        )
        response = self.client.get(url)
        expected = reverse(
            "admin:field_data_sample_genericmeasurement_change",
            args=[self.sample.pk, self.measurement.pk],
        )
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    def test_post_does_not_redirect_to_sample_scoped_url(self):
        """POST must NOT redirect — form data would be silently discarded."""
        url = reverse(
            "admin:analysis_genericmeasurement_change",
            args=[self.measurement.pk],
        )
        sample_scoped_change = reverse(
            "admin:field_data_sample_genericmeasurement_change",
            args=[self.sample.pk, self.measurement.pk],
        )
        response = self.client.post(url, data={})
        self.assertNotEqual(response.get("Location"), sample_scoped_change)


# ===========================================================================
# get_changeform_initial_data — sample pre-fill
# ===========================================================================


class InitialDataTest(_AdminSetup):

    def test_sample_pre_filled_on_sample_scoped_add(self):
        """Add form via sample-scoped URL must have sample FK pre-selected."""
        url = reverse(
            "admin:field_data_sample_genericmeasurement_add",
            args=[self.sample.pk],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context_data["adminform"].form
        self.assertEqual(str(form.initial.get("sample")), str(self.sample.pk))

    def test_sample_pre_filled_via_changelist_filters(self):
        """Add form reached with _changelist_filters must pre-fill sample."""
        from urllib.parse import urlencode

        pf = urlencode(
            {"_changelist_filters": f"sample__id__exact={self.sample.pk}"}
        )
        url = reverse("admin:analysis_genericmeasurement_add")
        # This GET would redirect, but we test the sample-scoped path directly
        # with the _changelist_filters preserved_filters param:
        scoped_url = reverse(
            "admin:field_data_sample_genericmeasurement_add",
            args=[self.sample.pk],
        )
        response = self.client.get(f"{scoped_url}?{pf}")
        self.assertEqual(response.status_code, 200)
        form = response.context_data["adminform"].form
        self.assertIn("sample", form.initial)


# ===========================================================================
# RawMeasurementAdmin — M2M ordering must not duplicate changelist rows
# (tech debt A5)
# ===========================================================================


class RawMeasurementAdminOrderingTest(TestCase):
    """RawMeasurementAdmin.ordering traverses the `sample` ManyToManyField
    (sample__location__project, sample__location) - a record linked to 2+
    samples must still appear exactly once in the changelist queryset."""

    @classmethod
    def setUpTestData(cls):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from analysis.models import RawMeasurement
        from laboratory.models import Device

        cls.superuser = User.objects.create_superuser(
            "rma_admin", "rma@test.com", "pw"
        )
        cls.project = Project.objects.create(
            title="RMA Test Project", label="RMA01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="RMA_LOC", data_source="internal", project=cls.project
        )
        cls.sample_a = Sample.objects.create(
            identifier="RMA_S_A", project=cls.project, location=cls.location
        )
        cls.sample_b = Sample.objects.create(
            identifier="RMA_S_B", project=cls.project, location=cls.location
        )
        cls.device = Device.objects.create(name="RMA Device")
        cls.researcher = Researcher.objects.create(
            user=User.objects.create_user(username="rma_researcher"),
            academic_rank="D",
            position="WiMa",
        )
        cls.multi_sample_measurement = RawMeasurement.objects.create(
            project=cls.project,
            device=cls.device,
            researcher=cls.researcher,
            file=SimpleUploadedFile("rma_test.txt", b"data"),
        )
        cls.multi_sample_measurement.sample.set([cls.sample_a, cls.sample_b])

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_changelist_queryset_has_no_duplicate_rows(self):
        from analysis.admin import RawMeasurementAdmin
        from analysis.models import RawMeasurement

        admin_instance = RawMeasurementAdmin(RawMeasurement, django_admin.site)
        request = RequestFactory().get("/")
        request.user = self.superuser
        qs = admin_instance.get_queryset(request)
        matches = list(qs.filter(pk=self.multi_sample_measurement.pk))
        self.assertEqual(len(matches), 1)

    def test_changelist_view_lists_measurement_once(self):
        url = reverse("admin:analysis_rawmeasurement_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context_data["cl"].result_count, 1
        )
