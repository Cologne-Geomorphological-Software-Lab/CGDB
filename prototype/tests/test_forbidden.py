"""Dead ends for restricted roles (#245).

A Viewer must not be offered actions they cannot run, must not see sidebar
links that end on a 403, must get a styled 403 page when they reach one
anyway, and must see one message, not two, when a record is out of reach.
"""

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import RequestFactory, TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm

from field_data.models import Location, Sample
from prototype.models import Project
from prototype.tests.roles import give_role


class _ViewerSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.viewer = User.objects.create_user(
            username="viewer_245", password="pw", is_staff=True
        )
        give_role(cls.viewer, "Viewer")
        cls.own_project = Project.objects.create(
            title="Own", label="OWN01", status="ACTIVE"
        )
        cls.other_project = Project.objects.create(
            title="Other", label="OTH01", status="ACTIVE"
        )
        assign_perm("view_project", cls.viewer, cls.own_project)
        location = Location.objects.create(
            identifier="OTH_LOC", data_source="internal", project=cls.other_project
        )
        cls.other_sample = Sample.objects.create(
            identifier="OTH_S01", project=cls.other_project, location=location
        )

    def setUp(self):
        self.client.force_login(self.viewer)


class ViewerDeleteActionTest(_ViewerSetup):
    def test_viewer_is_not_offered_delete_selected(self):
        admin_instance = django_admin.site._registry[Sample]
        request = RequestFactory().get(
            reverse("admin:field_data_sample_changelist")
        )
        request.user = self.viewer
        self.assertNotIn("delete_selected", admin_instance.get_actions(request))


class ForbiddenPageTest(_ViewerSetup):
    def test_forbidden_page_is_styled_and_offers_a_way_back(self):
        """A Viewer has no auth.view_user; the 403 keeps the admin layout."""
        response = self.client.get(reverse("admin:auth_user_changelist"))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")
        self.assertContains(response, "Access denied", status_code=403)
        self.assertContains(
            response, reverse("admin:index"), status_code=403
        )

    def test_viewer_can_open_data_sources(self):
        """The sidebar entry no longer ends on a 403: Viewers may view it."""
        response = self.client.get(
            reverse("admin:raster_data_datasource_changelist")
        )
        self.assertEqual(response.status_code, 200)


class InaccessibleRecordMessageTest(_ViewerSetup):
    def test_one_message_for_a_sample_of_another_project(self):
        response = self.client.get(
            reverse(
                "admin:field_data_sample_change", args=[self.other_sample.pk]
            )
        )
        self.assertEqual(response.status_code, 302)
        stored = list(get_messages(response.wsgi_request))
        self.assertEqual(len(stored), 1, [str(m) for m in stored])
