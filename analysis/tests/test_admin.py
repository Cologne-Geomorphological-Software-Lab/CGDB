"""Integration tests for SampleContextMixin in analysis/admin.py.

Tests cover the redirect logic that keeps all measurement forms under the
Sample URL hierarchy:
- changelist_view: redirects when sample__id__exact is in GET (GET only)
- add_view: redirects when sample is in GET (GET only, not POST)
- change_view: redirects when obj has sample_id (GET only, not POST)
- get_changeform_initial_data: pre-fills sample FK from preserved_filters
"""

from typing import TYPE_CHECKING, cast

from django.contrib import admin as django_admin
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse, HttpResponseRedirect
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ModelMultipleChoiceField
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from django.utils.datastructures import MultiValueDict

from analysis.models import GenericMeasurement, Parameter
from field_data.models import Location, Sample
from laboratory.models import Method
from prototype.models import Project, Researcher

if TYPE_CHECKING:
    from prototype.mixins import AuthenticatedHttpRequest


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
        assert response.context_data is not None
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
        assert response.context_data is not None
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
        qs = admin_instance.get_queryset(
            cast("AuthenticatedHttpRequest", request)
        )
        matches = list(qs.filter(pk=self.multi_sample_measurement.pk))
        self.assertEqual(len(matches), 1)

    def test_changelist_view_lists_measurement_once(self):
        url = reverse("admin:analysis_rawmeasurement_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        assert response.context_data is not None
        self.assertEqual(
            response.context_data["cl"].result_count, 1
        )


# ===========================================================================
# "Save" returns to the sample's analysis tab, with the success message (#242)
# ===========================================================================


class SaveRedirectTest(_AdminSetup):
    """A plain "Save" keeps Django's success message and lands on the tab.

    The mixin used to intercept response_add/response_change before Django
    added the message, so the user saw the sample form with no feedback.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.measurement = GenericMeasurement.objects.create(
            sample=cls.sample,
            method=cls.method,
            parameter=cls.parameter,
            value=1.0,
        )

    @property
    def admin_instance(self):
        # Not a setUpTestData attribute: Django deep-copies those per test,
        # and a ModelAdmin instance cannot be copied.
        return django_admin.site._registry[GenericMeasurement]

    def _post_request(self, button: str) -> "AuthenticatedHttpRequest":
        """A POST as the admin's change form sends it, with message storage."""
        request = RequestFactory().post("/", {button: "1"})
        request.user = self.superuser
        SessionMiddleware(lambda _r: HttpResponse()).process_request(request)
        # The messages framework reads this private attribute; outside the
        # middleware stack it has to be attached by hand.
        setattr(request, "_messages", FallbackStorage(request))  # noqa: B010
        return cast("AuthenticatedHttpRequest", request)

    def _assert_tab_redirect_with_message(
        self,
        request: "AuthenticatedHttpRequest",
        response: HttpResponse,
        verb: str,
    ) -> None:
        assert isinstance(response, HttpResponseRedirect)
        self.assertEqual(
            response.url,
            reverse(
                "admin:field_data_sample_genericmeasurement",
                args=[self.sample.pk],
            ),
        )
        stored = list(get_messages(request))
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].level, messages.SUCCESS)
        self.assertIn(f"was {verb} successfully", str(stored[0]))

    def test_add_redirects_to_tab_with_message(self):
        request = self._post_request("_save")
        response = self.admin_instance.response_add(request, self.measurement)
        self._assert_tab_redirect_with_message(request, response, "added")

    def test_change_redirects_to_tab_with_message(self):
        request = self._post_request("_save")
        response = self.admin_instance.response_change(
            request, self.measurement
        )
        self._assert_tab_redirect_with_message(request, response, "changed")

    def test_save_and_continue_is_left_to_django(self):
        response = self.admin_instance.response_change(
            self._post_request("_continue"), self.measurement
        )
        assert isinstance(response, HttpResponseRedirect)
        self.assertNotIn("/field_data/sample/", response.url)


# ===========================================================================
# RawMeasurement: every sample must belong to the measurement's project (#244)
# ===========================================================================


class RawMeasurementProjectMatchTest(TestCase):
    """The admin form rejects samples of other projects and names them."""

    @classmethod
    def setUpTestData(cls):
        from analysis.models import RawMeasurement
        from laboratory.models import Device

        cls.superuser = User.objects.create_superuser(
            "rmp_admin", "rmp@test.com", "pw"
        )
        cls.project_a = Project.objects.create(
            title="RMP Project A", label="RMP01", status="ACTIVE"
        )
        cls.project_b = Project.objects.create(
            title="RMP Project B", label="RMP02", status="ACTIVE"
        )
        location_a = Location.objects.create(
            identifier="RMP_LOC_A", data_source="internal", project=cls.project_a
        )
        location_b = Location.objects.create(
            identifier="RMP_LOC_B", data_source="internal", project=cls.project_b
        )
        cls.sample_a = Sample.objects.create(
            identifier="RMP_S_A", project=cls.project_a, location=location_a
        )
        cls.sample_b = Sample.objects.create(
            identifier="RMP_S_B", project=cls.project_b, location=location_b
        )
        cls.device = Device.objects.create(name="RMP Device")
        cls.researcher = Researcher.objects.create(
            user=User.objects.create_user(username="rmp_researcher"),
            academic_rank="D",
            position="WiMa",
        )
        cls.measurement = RawMeasurement.objects.create(
            project=cls.project_a,
            device=cls.device,
            researcher=cls.researcher,
            file=SimpleUploadedFile("rmp_a.txt", b"data"),
        )
        cls.measurement.sample.set([cls.sample_a])

    def _form(self, samples):
        from analysis.admin import RawMeasurementAdminForm

        return RawMeasurementAdminForm(
            data={
                "project": self.project_a.pk,
                "sample": [s.pk for s in samples],
                "device": self.device.pk,
                "researcher": self.researcher.pk,
            },
            files=MultiValueDict(
                {"file": [SimpleUploadedFile("rmp.txt", b"data")]}
            ),
        )

    def test_samples_of_the_own_project_are_accepted(self):
        form = self._form([self.sample_a])
        self.assertTrue(form.is_valid(), form.errors)

    def test_sample_of_another_project_is_rejected_by_name(self):
        form = self._form([self.sample_a, self.sample_b])
        self.assertFalse(form.is_valid())
        self.assertIn("RMP_S_B", form.errors["sample"][0])
        self.assertNotIn("RMP_S_A", form.errors["sample"][0])

    def test_change_form_offers_only_samples_of_the_project(self):
        from analysis.models import RawMeasurement

        admin_instance = django_admin.site._registry[RawMeasurement]
        url = reverse(
            "admin:analysis_rawmeasurement_change", args=[self.measurement.pk]
        )
        request = RequestFactory().get(url)
        request.user = self.superuser
        request.resolver_match = resolve(url)
        field = admin_instance.get_form(cast("AuthenticatedHttpRequest", request))().fields["sample"]
        assert isinstance(field, ModelMultipleChoiceField)
        assert field.queryset is not None
        offered = list(field.queryset)
        self.assertIn(self.sample_a, offered)
        self.assertNotIn(self.sample_b, offered)
