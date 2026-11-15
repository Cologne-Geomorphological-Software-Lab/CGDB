"""RawMeasurementAdmin must check the measurement's project, not only the role.

RawMeasurement.sample is a many-to-many field, so the old project_path
"sample__location__project" never reached a project: the object checks fell
back to the role permission alone. A Researcher who could only *view*
another project could then change and delete its raw measurements.
"""

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from guardian.shortcuts import assign_perm

from analysis.models import RawMeasurement
from laboratory.models import Device
from prototype.models import Project, Researcher
from prototype.tests.roles import give_role


class RawMeasurementProjectScopeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(title="P", label="P")
        cls.raw = RawMeasurement.objects.create(
            project=cls.project,
            device=Device.objects.create(name="RM device"),
            researcher=Researcher.objects.create(
                academic_rank="D", position="WiMa"
            ),
            file=SimpleUploadedFile("raw.bin", b"raw"),
        )
        cls.viewing_researcher = give_role(
            User.objects.create_user(
                username="rm_view_only", password="pw", is_staff=True
            ),
            "Researcher",
        )
        assign_perm("view_project", cls.viewing_researcher, cls.project)
        cls.editing_researcher = give_role(
            User.objects.create_user(
                username="rm_editor", password="pw", is_staff=True
            ),
            "Researcher",
        )
        for perm in ("view_project", "change_project"):
            assign_perm(perm, cls.editing_researcher, cls.project)

    def _request(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return request

    def test_view_only_member_cannot_change_or_delete(self):
        raw_admin = admin.site._registry[RawMeasurement]
        request = self._request(self.viewing_researcher)
        self.assertTrue(raw_admin.has_view_permission(request, self.raw))
        self.assertFalse(raw_admin.has_change_permission(request, self.raw))
        self.assertFalse(raw_admin.has_delete_permission(request, self.raw))

    def test_member_with_change_permission_can_change(self):
        raw_admin = admin.site._registry[RawMeasurement]
        request = self._request(self.editing_researcher)
        self.assertTrue(raw_admin.has_change_permission(request, self.raw))
