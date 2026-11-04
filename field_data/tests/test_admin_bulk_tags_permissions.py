"""Tests that the bulk tag actions follow the same rules as the edit forms."""

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm

from field_data.models import Location, Sample, Tag
from prototype.models import Project
from prototype.permissions import create_permission_groups


class BulkTagPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # post_migrate fills the groups before every app's permissions exist
        # on a fresh database, as the test database is.
        create_permission_groups()
        cls.project_a = Project.objects.create(
            title="Project A", label="A", status="ACTIVE"
        )
        cls.project_b = Project.objects.create(
            title="Project B", label="B", status="ACTIVE"
        )
        cls.viewer = cls._user("tagperm_viewer", "Viewer")
        assign_perm("view_project", cls.viewer, cls.project_a)

        # Can edit project A but only read project B, so a single changelist
        # selection can mix records the user may and may not change.
        cls.researcher = cls._user("tagperm_researcher", "Researcher")
        for perm in ("view_project", "change_project"):
            assign_perm(perm, cls.researcher, cls.project_a)
        assign_perm("view_project", cls.researcher, cls.project_b)

        location_a = Location.objects.create(
            identifier="LOC-A", project=cls.project_a, data_source="internal"
        )
        location_b = Location.objects.create(
            identifier="LOC-B", project=cls.project_b, data_source="internal"
        )
        cls.sample_a = Sample.objects.create(
            identifier="S-A", project=cls.project_a, location=location_a
        )
        cls.sample_b = Sample.objects.create(
            identifier="S-B", project=cls.project_b, location=location_b
        )
        content_type = ContentType.objects.get_for_model(Sample)
        cls.tag_a = Tag.objects.create(
            word="tag-a", content_type=content_type, project=cls.project_a
        )
        cls.tag_b = Tag.objects.create(
            word="tag-b", content_type=content_type, project=cls.project_b
        )
        cls.url = reverse("admin:field_data_sample_changelist")

    @classmethod
    def _user(cls, name, group):
        user = User.objects.create_user(
            username=name, password="pw", is_staff=True
        )
        user.groups.add(Group.objects.get(name=group))
        return user

    def _apply(self, action, samples, tags):
        return self.client.post(
            self.url,
            {
                "action": action,
                ACTION_CHECKBOX_NAME: [s.pk for s in samples],
                "_apply_tag_action": "1",
                "tags": [t.pk for t in tags],
            },
            follow=True,
        )

    def test_viewer_is_not_offered_the_actions(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertNotContains(response, "add_tags_to_selected")
        self.assertNotContains(response, "remove_tags_from_selected")

    def test_viewer_cannot_add_tags_with_a_crafted_post(self):
        self.client.force_login(self.viewer)
        self._apply("add_tags_to_selected", [self.sample_a], [self.tag_a])
        self.assertFalse(self.sample_a.tags.exists())

    def test_viewer_cannot_remove_tags_with_a_crafted_post(self):
        self.sample_a.tags.add(self.tag_a)
        self.client.force_login(self.viewer)
        self._apply("remove_tags_from_selected", [self.sample_a], [self.tag_a])
        self.assertTrue(self.sample_a.tags.filter(pk=self.tag_a.pk).exists())

    def test_researcher_is_offered_the_actions(self):
        self.client.force_login(self.researcher)
        response = self.client.get(self.url)
        self.assertContains(response, "add_tags_to_selected")

    def test_researcher_tags_record_in_own_project(self):
        self.client.force_login(self.researcher)
        self._apply("add_tags_to_selected", [self.sample_a], [self.tag_a])
        self.assertTrue(self.sample_a.tags.filter(pk=self.tag_a.pk).exists())

    def test_mixed_selection_only_changes_permitted_records(self):
        self.client.force_login(self.researcher)
        response = self._apply(
            "add_tags_to_selected",
            [self.sample_a, self.sample_b],
            [self.tag_a],
        )
        self.assertTrue(self.sample_a.tags.exists())
        self.assertFalse(self.sample_b.tags.exists())
        self.assertContains(response, "1 selected record")

    def test_tag_of_read_only_project_is_not_applicable(self):
        self.client.force_login(self.researcher)
        self._apply(
            "add_tags_to_selected",
            [self.sample_a, self.sample_b],
            [self.tag_b],
        )
        self.assertFalse(self.sample_a.tags.exists())
        self.assertFalse(self.sample_b.tags.exists())

    def test_selection_without_permitted_records_changes_nothing(self):
        self.client.force_login(self.researcher)
        response = self._apply(
            "add_tags_to_selected", [self.sample_b], [self.tag_b]
        )
        self.assertFalse(self.sample_b.tags.exists())
        self.assertContains(response, "no permission")

    def test_change_is_written_to_the_admin_log(self):
        self.client.force_login(self.researcher)
        self._apply("add_tags_to_selected", [self.sample_a], [self.tag_a])
        entry = LogEntry.objects.get(
            user=self.researcher,
            content_type=ContentType.objects.get_for_model(Sample),
            object_id=str(self.sample_a.pk),
        )
        self.assertEqual(entry.action_flag, CHANGE)
        self.assertIn("tag-a", entry.change_message)
