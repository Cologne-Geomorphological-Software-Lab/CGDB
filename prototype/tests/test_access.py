"""Tests for prototype.access, the shared project access rules."""

from types import SimpleNamespace

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from guardian.shortcuts import assign_perm

from field_data.models import Location
from prototype.access import (
    accessible_projects,
    addable_projects,
    has_project_perm,
    require_project_perm,
    resolve_project,
    scope_to_accessible_projects,
)
from prototype.models import Project


class ResolveProjectTest(TestCase):
    def test_first_path_with_a_project_wins(self):
        direct = SimpleNamespace()
        nested = SimpleNamespace()
        obj = SimpleNamespace(
            project=direct, location=SimpleNamespace(project=nested)
        )
        self.assertIs(
            resolve_project(obj, ("project", "location__project")), direct
        )

    def test_falls_back_to_later_path(self):
        nested = SimpleNamespace()
        obj = SimpleNamespace(
            project=None, location=SimpleNamespace(project=nested)
        )
        self.assertIs(
            resolve_project(obj, ("project", "location__project")), nested
        )

    def test_missing_link_returns_none(self):
        obj = SimpleNamespace(sample=None)
        self.assertIsNone(resolve_project(obj, ("sample__location__project",)))

    def test_missing_attribute_returns_none(self):
        self.assertIsNone(resolve_project(SimpleNamespace(), ("project",)))


class ProjectPermissionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project_a = Project.objects.create(title="A", label="A")
        cls.project_b = Project.objects.create(title="B", label="B")
        cls.user = User.objects.create_user(username="member", password="pw")
        assign_perm("view_project", cls.user, cls.project_a)
        assign_perm("add_project", cls.user, cls.project_a)
        cls.superuser = User.objects.create_superuser(
            username="root", password="pw", email="root@test.com"
        )

    def test_accessible_and_addable_projects(self):
        self.assertEqual(list(accessible_projects(self.user)), [self.project_a])
        self.assertEqual(list(addable_projects(self.user)), [self.project_a])

    def test_has_project_perm(self):
        self.assertTrue(has_project_perm(self.user, "view", self.project_a))
        self.assertFalse(has_project_perm(self.user, "change", self.project_a))
        self.assertFalse(has_project_perm(self.user, "view", self.project_b))
        self.assertTrue(
            has_project_perm(self.superuser, "delete", self.project_b)
        )

    def test_require_project_perm_denies_with_action_message(self):
        with self.assertRaisesMessage(
            PermissionDenied,
            "You do not have permission to change data in this project.",
        ):
            require_project_perm(self.user, "change", self.project_a)

    def test_require_project_perm_denies_missing_project(self):
        with self.assertRaises(PermissionDenied):
            require_project_perm(self.user, "view", None)

    def test_require_project_perm_lets_superuser_through(self):
        require_project_perm(self.superuser, "delete", None)

    def test_scope_to_accessible_projects(self):
        Location.objects.create(identifier="LA", project=self.project_a)
        Location.objects.create(identifier="LB", project=self.project_b)
        qs = Location.objects.all()
        self.assertEqual(
            list(
                scope_to_accessible_projects(self.user, qs).values_list(
                    "identifier", flat=True
                )
            ),
            ["LA"],
        )
        self.assertEqual(
            scope_to_accessible_projects(self.superuser, qs).count(), 2
        )
