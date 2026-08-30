"""Tests for the admin-layer reparenting IDOR fix (prototype/mixins.py).

Covers all three project-chain mixins used across the admin — a user with
change_project on an object's current project must not be able to silently
move that object into a different project via its FK dropdown unless they
also have add_project there:

- ProjectBasedPermissionMixin (via CampaignAdmin's direct "project" field)
- NestedProjectPermissionMixin (via SiteAdmin's "study_area" field, chained
  through StudyArea.project)
- HybridProjectPermissionMixin (via SampleAdmin's "project" and "location"
  fields)

Each admin class gets both an end-to-end HTTP test (proving the two layers
together — formfield_for_foreignkey's dropdown restriction and save_model's
PermissionDenied backstop — reject the write) and a direct save_model() unit
test that bypasses the dropdown restriction entirely, proving save_model's
own check is a real, independent layer rather than dead code that only
looks reachable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from django.contrib.admin import site as django_admin_site
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm

from field_data.admin import CampaignAdmin, SampleAdmin, SiteAdmin
from field_data.models import Campaign, Location, Sample, Site, StudyArea
from prototype.models import Project

if TYPE_CHECKING:
    from django.forms import ModelForm

    from prototype.mixins import AuthenticatedHttpRequest

# save_model()'s form param is only ever passed through to super(), never read
# by these mixins — tests don't need a real ModelForm instance.
_NO_FORM = cast("ModelForm", None)


def _make_request(url: str, user: User) -> AuthenticatedHttpRequest:
    request = RequestFactory().post(url)
    request.user = user
    return cast("AuthenticatedHttpRequest", request)


def _form_post_data(response, overrides: dict) -> dict:
    """Build a full, valid changeform POST body from a GET response.

    Starts from the bound form's initial values (already PK-shaped for FK/M2M
    fields, matching what a real submission would send) so every other
    required field stays populated, then applies the specific overrides the
    test cares about.
    """
    form = response.context["adminform"].form
    data = {}
    for name, field in form.fields.items():
        value = form.initial.get(name, field.initial)
        if value is None:
            continue
        if hasattr(value, "pk"):
            value = value.pk
        elif isinstance(value, (list, tuple)) or hasattr(value, "all"):
            value = [getattr(v, "pk", v) for v in value]
        data[name] = value
    data.update(overrides)
    data["_save"] = "Save"
    return data


class _ReparentingSetup(TestCase):
    """Three projects, one editor user:

    - project_a: editor has view_project + change_project only (NOT
      add_project) — the "current project, editable but not addable" case.
    - project_b: editor has no permission at all — the forbidden target.
    - project_c: editor has view_project + add_project — a valid target to
      reparent into.
    """

    project_a: ClassVar[Project]
    project_b: ClassVar[Project]
    project_c: ClassVar[Project]
    editor: ClassVar[User]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.project_a = Project.objects.create(
            title="Project A", label="RPA01", status="ACTIVE"
        )
        cls.project_b = Project.objects.create(
            title="Project B", label="RPB01", status="ACTIVE"
        )
        cls.project_c = Project.objects.create(
            title="Project C", label="RPC01", status="ACTIVE"
        )
        cls.editor = User.objects.create_user(
            username="reparent_editor", password="pw", is_staff=True
        )
        assign_perm("view_project", cls.editor, cls.project_a)
        assign_perm("change_project", cls.editor, cls.project_a)
        assign_perm("view_project", cls.editor, cls.project_c)
        assign_perm("add_project", cls.editor, cls.project_c)
        # No permissions of any kind on project_b.

    def setUp(self) -> None:
        self.client: Client = Client()
        self.client.force_login(self.editor)

    def _assert_write_rejected(self, resp) -> None:
        """The write must not have gone through.

        Either PermissionDenied (403) from save_model, or a form-validation
        rejection (200, re-rendered with the offending choice missing from
        the field's queryset) from formfield_for_foreignkey — both are valid
        outcomes of the combined protection. A 302 redirect (a completed,
        successful save) is not.
        """
        self.assertNotEqual(resp.status_code, 302)
        self.assertIn(resp.status_code, (200, 403))


class CampaignReparentingTest(_ReparentingSetup):
    """CampaignAdmin uses ProjectBasedPermissionMixin — direct "project" field."""

    campaign: ClassVar[Campaign]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.campaign = Campaign.objects.create(
            label="RP_CAMP", project=cls.project_a
        )

    def _change_url(self) -> str:
        return reverse(
            "admin:field_data_campaign_change", args=[self.campaign.pk]
        )

    def test_edit_without_touching_project_succeeds_despite_no_add_on_current(
        self,
    ) -> None:
        """Editor only has change_project (not add_project) on project_a."""
        url = self._change_url()
        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, 200)
        data = _form_post_data(get_resp, {"label": "RP_CAMP_RENAMED"})
        resp = self.client.post(url, data)
        self.assertNotEqual(resp.status_code, 403)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.label, "RP_CAMP_RENAMED")
        self.assertEqual(self.campaign.project.pk, self.project_a.pk)

    def test_reparent_to_project_without_add_permission_is_rejected(
        self,
    ) -> None:
        url = self._change_url()
        get_resp = self.client.get(url)
        data = _form_post_data(get_resp, {"project": self.project_b.pk})
        resp = self.client.post(url, data)
        self._assert_write_rejected(resp)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.project.pk, self.project_a.pk)

    def test_reparent_to_project_with_add_permission_succeeds(self) -> None:
        url = self._change_url()
        get_resp = self.client.get(url)
        data = _form_post_data(get_resp, {"project": self.project_c.pk})
        resp = self.client.post(url, data)
        self.assertNotEqual(resp.status_code, 403)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.project.pk, self.project_c.pk)

    def test_project_dropdown_excludes_inaccessible_project(self) -> None:
        url = self._change_url()
        resp = self.client.get(url)
        field = resp.context["adminform"].form.fields["project"]
        choice_pks = {obj.pk for obj in field.queryset}
        self.assertIn(self.project_a.pk, choice_pks)  # current value, kept
        self.assertIn(self.project_c.pk, choice_pks)  # addable
        self.assertNotIn(self.project_b.pk, choice_pks)  # no permission

    def test_save_model_rejects_reparenting_even_with_no_dropdown_restriction(
        self,
    ) -> None:
        """Direct save_model() call, bypassing form/queryset validation entirely.

        Proves save_model's own PermissionDenied check is a real,
        independent layer — not dead code that merely looks reachable
        because formfield_for_foreignkey already filters the choices.
        """
        admin = CampaignAdmin(Campaign, django_admin_site)
        request = _make_request(self._change_url(), self.editor)
        obj = Campaign.objects.get(pk=self.campaign.pk)
        obj.project = self.project_b  # bypasses the ModelChoiceField entirely
        with self.assertRaises(PermissionDenied):
            admin.save_model(request, obj, form=_NO_FORM, change=True)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.project.pk, self.project_a.pk)


class SiteReparentingTest(_ReparentingSetup):
    """SiteAdmin uses NestedProjectPermissionMixin — "study_area" field,
    project_path="study_area__project".
    """

    study_area_a: ClassVar[StudyArea]
    study_area_b: ClassVar[StudyArea]
    study_area_c: ClassVar[StudyArea]
    site: ClassVar[Site]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.study_area_a = StudyArea.objects.create(
            label="RP_SA_A", project=cls.project_a
        )
        cls.study_area_b = StudyArea.objects.create(
            label="RP_SA_B", project=cls.project_b
        )
        cls.study_area_c = StudyArea.objects.create(
            label="RP_SA_C", project=cls.project_c
        )
        cls.site = Site.objects.create(
            label="RP_SITE", study_area=cls.study_area_a
        )

    def _change_url(self) -> str:
        return reverse("admin:field_data_site_change", args=[self.site.pk])

    def test_edit_without_touching_study_area_succeeds_despite_no_add_on_current(
        self,
    ) -> None:
        url = self._change_url()
        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, 200)
        data = _form_post_data(get_resp, {"label": "RP_SITE_RENAMED"})
        resp = self.client.post(url, data)
        self.assertNotEqual(resp.status_code, 403)
        self.site.refresh_from_db()
        self.assertEqual(self.site.label, "RP_SITE_RENAMED")
        self.assertEqual(self.site.study_area.pk, self.study_area_a.pk)

    def test_reparent_to_study_area_without_add_permission_is_rejected(
        self,
    ) -> None:
        url = self._change_url()
        get_resp = self.client.get(url)
        data = _form_post_data(
            get_resp, {"study_area": self.study_area_b.pk}
        )
        resp = self.client.post(url, data)
        self._assert_write_rejected(resp)
        self.site.refresh_from_db()
        self.assertEqual(self.site.study_area.pk, self.study_area_a.pk)

    def test_reparent_to_study_area_with_add_permission_succeeds(
        self,
    ) -> None:
        url = self._change_url()
        get_resp = self.client.get(url)
        data = _form_post_data(
            get_resp, {"study_area": self.study_area_c.pk}
        )
        resp = self.client.post(url, data)
        self.assertNotEqual(resp.status_code, 403)
        self.site.refresh_from_db()
        self.assertEqual(self.site.study_area.pk, self.study_area_c.pk)

    def test_study_area_dropdown_excludes_inaccessible_project(self) -> None:
        url = self._change_url()
        resp = self.client.get(url)
        field = resp.context["adminform"].form.fields["study_area"]
        choice_pks = {obj.pk for obj in field.queryset}
        self.assertIn(self.study_area_a.pk, choice_pks)  # current, kept
        self.assertIn(self.study_area_c.pk, choice_pks)  # addable
        self.assertNotIn(self.study_area_b.pk, choice_pks)  # no permission

    def test_save_model_rejects_reparenting_even_with_no_dropdown_restriction(
        self,
    ) -> None:
        admin = SiteAdmin(Site, django_admin_site)
        request = _make_request(self._change_url(), self.editor)
        obj = Site.objects.get(pk=self.site.pk)
        obj.study_area = self.study_area_b
        with self.assertRaises(PermissionDenied):
            admin.save_model(request, obj, form=_NO_FORM, change=True)
        self.site.refresh_from_db()
        self.assertEqual(self.site.study_area.pk, self.study_area_a.pk)


class SampleReparentingTest(_ReparentingSetup):
    """SampleAdmin uses HybridProjectPermissionMixin — direct "project" field
    plus the indirect "location" field (handled by SampleAdmin's own
    formfield_for_foreignkey override in field_data/admin.py).

    Sample.clean() requires project and location.project to match, so
    reparenting tests move both fields together.
    """

    sample: ClassVar[Sample]
    location_a: ClassVar[Location]
    location_b: ClassVar[Location]
    location_c: ClassVar[Location]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.location_a = Location.objects.create(
            identifier="RP_LOC_A", data_source="internal", project=cls.project_a
        )
        cls.location_b = Location.objects.create(
            identifier="RP_LOC_B", data_source="internal", project=cls.project_b
        )
        cls.location_c = Location.objects.create(
            identifier="RP_LOC_C", data_source="internal", project=cls.project_c
        )
        cls.sample = Sample.objects.create(
            identifier="RP_SAMPLE", project=cls.project_a, location=cls.location_a
        )

    def _change_url(self) -> str:
        return reverse("admin:field_data_sample_change", args=[self.sample.pk])

    def test_reparent_to_project_without_add_permission_is_rejected(
        self,
    ) -> None:
        url = self._change_url()
        get_resp = self.client.get(url)
        data = _form_post_data(
            get_resp,
            {"project": self.project_b.pk, "location": self.location_b.pk},
        )
        resp = self.client.post(url, data)
        self._assert_write_rejected(resp)
        self.sample.refresh_from_db()
        self.assertEqual(self.sample.project.pk, self.project_a.pk)

    def test_reparent_to_project_with_add_permission_succeeds(
        self,
    ) -> None:
        url = self._change_url()
        get_resp = self.client.get(url)
        data = _form_post_data(
            get_resp,
            {"project": self.project_c.pk, "location": self.location_c.pk},
        )
        resp = self.client.post(url, data)
        self.assertNotEqual(resp.status_code, 403)
        self.sample.refresh_from_db()
        self.assertEqual(self.sample.project.pk, self.project_c.pk)
        self.assertEqual(self.sample.location.pk, self.location_c.pk)

    def test_project_dropdown_excludes_inaccessible_project(self) -> None:
        url = self._change_url()
        resp = self.client.get(url)
        field = resp.context["adminform"].form.fields["project"]
        choice_pks = {obj.pk for obj in field.queryset}
        self.assertIn(self.project_a.pk, choice_pks)  # current, kept
        self.assertIn(self.project_c.pk, choice_pks)  # addable
        self.assertNotIn(self.project_b.pk, choice_pks)  # no permission

    def test_location_dropdown_excludes_location_in_inaccessible_project(
        self,
    ) -> None:
        url = self._change_url()
        resp = self.client.get(url)
        field = resp.context["adminform"].form.fields["location"]
        choice_pks = {obj.pk for obj in field.queryset}
        self.assertIn(self.location_a.pk, choice_pks)  # current, kept
        self.assertIn(self.location_c.pk, choice_pks)  # addable project
        self.assertNotIn(self.location_b.pk, choice_pks)  # no permission

    def test_save_model_rejects_reparenting_even_with_no_dropdown_restriction(
        self,
    ) -> None:
        admin = SampleAdmin(Sample, django_admin_site)
        request = _make_request(self._change_url(), self.editor)
        obj = Sample.objects.get(pk=self.sample.pk)
        obj.project = self.project_b
        with self.assertRaises(PermissionDenied):
            admin.save_model(request, obj, form=_NO_FORM, change=True)
        self.sample.refresh_from_db()
        self.assertEqual(self.sample.project.pk, self.project_a.pk)
