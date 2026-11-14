"""Access needs the role permission AND the project permission.

Project membership grants view, add and change on the project
(prototype/admin.py, _MEMBER_PERMS). The role group decides what the user
may do with each model. Before this rule, a Viewer who was a project member
could edit that project's data in the admin and through the API.
"""

from typing import TYPE_CHECKING, cast

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm
from rest_framework.test import APIClient

from field_data.models import Location, StudyArea
from prototype.permissions import create_permission_groups
from prototype.models import Project

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse as TestResponse

_MEMBER_PERMS = ("view_project", "add_project", "change_project")
_POINT = {"type": "Point", "coordinates": [7.0, 51.0]}
_POLYGON = {
    "type": "Polygon",
    "coordinates": [[[7, 50], [8, 50], [8, 51], [7, 51], [7, 50]]],
}


class RoleAndProjectTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        create_permission_groups()
        cls.project = Project.objects.create(title="P", label="P")
        cls.viewer = cls._member("rp_viewer", "Viewer")
        cls.researcher = cls._member("rp_researcher", "Researcher")
        cls.no_role = cls._member("rp_no_role", None)
        cls.location = Location.objects.create(
            identifier="RP-1", project=cls.project, data_source="internal"
        )

    @classmethod
    def _member(cls, name, group):
        user = User.objects.create_user(
            username=name, password="pw", is_staff=True
        )
        if group:
            user.groups.add(Group.objects.get(name=group))
        for perm in _MEMBER_PERMS:
            assign_perm(perm, user, cls.project)
        return user

    def _admin_request(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return request

    def _api(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    # --- admin -------------------------------------------------------------

    def test_viewer_member_cannot_add_change_or_delete_in_admin(self):
        location_admin = admin.site._registry[Location]
        request = self._admin_request(self.viewer)
        location = Location.objects.get(pk=self.location.pk)
        self.assertTrue(location_admin.has_view_permission(request, location))
        self.assertFalse(location_admin.has_add_permission(request))
        self.assertFalse(
            location_admin.has_change_permission(request, location)
        )
        self.assertFalse(location_admin.has_change_permission(request))
        self.assertFalse(location_admin.has_delete_permission(request))

    def test_researcher_member_can_add_and_change_in_admin(self):
        location_admin = admin.site._registry[Location]
        request = self._admin_request(self.researcher)
        location = Location.objects.get(pk=self.location.pk)
        self.assertTrue(location_admin.has_add_permission(request))
        self.assertTrue(
            location_admin.has_change_permission(request, location)
        )
        # Researchers have no delete permission in any role group.
        self.assertFalse(
            location_admin.has_delete_permission(request, location)
        )

    def test_member_without_role_cannot_open_the_changelist(self):
        self.client.force_login(self.no_role)
        response = self.client.get(
            reverse("admin:field_data_location_changelist")
        )
        self.assertEqual(response.status_code, 403)

    def test_viewer_is_not_offered_delete_selected(self):
        self.client.force_login(self.viewer)
        response = self.client.get(
            reverse("admin:field_data_location_changelist")
        )
        self.assertEqual(response.status_code, 200)
        # Without any permitted action Django renders no action form at all.
        action_form = response.context["action_form"]
        actions = (
            [name for name, _ in action_form.fields["action"].choices]
            if action_form is not None
            else []
        )
        self.assertNotIn("delete_selected", actions)

    # --- API ---------------------------------------------------------------

    def test_viewer_member_cannot_write_through_the_api(self):
        api = self._api(self.viewer)
        patch = cast("TestResponse", api.patch(
            f"/api/v1/locations/{self.location.pk}/",
            {"location": _POINT},
            format="json",
        ))
        self.assertEqual(patch.status_code, 403)
        post = cast("TestResponse", api.post(
            "/api/v1/study-areas/",
            {"label": "SA-V", "project": self.project.pk, "geometry": _POLYGON},
            format="json",
        ))
        self.assertEqual(post.status_code, 403)
        self.assertFalse(StudyArea.objects.filter(label="SA-V").exists())

    def test_viewer_member_can_read_through_the_api(self):
        response = cast("TestResponse", self._api(self.viewer).get("/api/v1/locations/"))
        self.assertEqual(response.status_code, 200)

    def test_researcher_member_can_write_through_the_api(self):
        api = self._api(self.researcher)
        patch = cast("TestResponse", api.patch(
            f"/api/v1/locations/{self.location.pk}/",
            {"location": _POINT},
            format="json",
        ))
        self.assertEqual(patch.status_code, 200)
        post = cast("TestResponse", api.post(
            "/api/v1/study-areas/",
            {"label": "SA-R", "project": self.project.pk, "geometry": _POLYGON},
            format="json",
        ))
        self.assertEqual(post.status_code, 201)

    def test_member_without_role_cannot_read_through_the_api(self):
        response = cast("TestResponse", self._api(self.no_role).get("/api/v1/locations/"))
        self.assertEqual(response.status_code, 403)

    # --- map dashboard -----------------------------------------------------

    def test_map_dashboard_offers_editing_only_to_roles_that_can_write(self):
        for user, expected in [(self.viewer, False), (self.researcher, True)]:
            self.client.force_login(user)
            response = self.client.get(reverse("map_dashboard"))
            self.assertEqual(response.status_code, 200)
            self.assertIs(response.context["can_edit"], expected, user)
