"""Tests for prototype signal handlers.

The signal assign_permissions_to_creator fires on post_save for any BaseModel
instance and uses transaction.on_commit() to assign Guardian object-level
permissions (view, change, delete) to the creator.

TestCase wraps tests in a transaction that is never committed, so
on_commit callbacks do not run by default. We use
captureOnCommitCallbacks(execute=True) to force execution within the test.
"""
from django.contrib.auth.models import Group, User
from django.test import TestCase

from guardian.shortcuts import assign_perm, get_perms, remove_perm

from prototype.models import Project, Researcher, ResearchGroup


class PermissionSignalTest(TestCase):
    """Tests for assign_permissions_to_creator signal."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="sig_user", password="pw")
        cls.other_user = User.objects.create_user(username="sig_other", password="pw")

    # ------------------------------------------------------------------
    # Happy path: permissions are assigned on creation
    # ------------------------------------------------------------------

    def test_view_permission_assigned_on_create(self):
        with self.captureOnCommitCallbacks(execute=True):
            project = Project.objects.create(
                title="SigTest1",
                label="SIG001",
                status="ACTIVE",
                created_by=self.user,
            )
        self.assertIn("view_project", get_perms(self.user, project))

    def test_change_permission_assigned_on_create(self):
        with self.captureOnCommitCallbacks(execute=True):
            project = Project.objects.create(
                title="SigTest2",
                label="SIG002",
                status="ACTIVE",
                created_by=self.user,
            )
        self.assertIn("change_project", get_perms(self.user, project))

    def test_delete_permission_assigned_on_create(self):
        with self.captureOnCommitCallbacks(execute=True):
            project = Project.objects.create(
                title="SigTest3",
                label="SIG003",
                status="ACTIVE",
                created_by=self.user,
            )
        self.assertIn("delete_project", get_perms(self.user, project))

    def test_all_three_permissions_assigned_together(self):
        """All three permissions are assigned in a single signal call."""
        with self.captureOnCommitCallbacks(execute=True):
            project = Project.objects.create(
                title="SigTest4",
                label="SIG004",
                status="ACTIVE",
                created_by=self.user,
            )
        perms = get_perms(self.user, project)
        self.assertIn("view_project", perms)
        self.assertIn("change_project", perms)
        self.assertIn("delete_project", perms)

    # ------------------------------------------------------------------
    # Signal does NOT fire for updates
    # ------------------------------------------------------------------

    def test_permissions_not_re_assigned_on_update(self):
        """Updating an existing object does not trigger permission assignment."""
        with self.captureOnCommitCallbacks(execute=True):
            project = Project.objects.create(
                title="SigUpdate1",
                label="SIGU01",
                status="ACTIVE",
                created_by=self.user,
            )

        # Remove one permission to verify update doesn't restore it
        remove_perm("view_project", self.user, project)
        self.assertNotIn("view_project", get_perms(self.user, project))

        # Update the project (not a creation)
        with self.captureOnCommitCallbacks(execute=True):
            project.title = "SigUpdate1 Modified"
            project.save()

        # Permission should still be absent – signal only fires on created=True
        self.assertNotIn("view_project", get_perms(self.user, project))

    # ------------------------------------------------------------------
    # Signal is benign when created_by is None
    # ------------------------------------------------------------------

    def test_no_error_when_created_by_is_none(self):
        """Signal silently skips permission assignment when created_by is None."""
        with self.captureOnCommitCallbacks(execute=True):
            project = Project.objects.create(
                title="NoPerm1",
                label="NP001",
                status="ACTIVE",
                # created_by not set → None
            )
        # No crash. No permissions assigned (no user to assign to).
        self.assertIsNone(project.created_by)

    # ------------------------------------------------------------------
    # Permissions are user-specific – other users don't receive them
    # ------------------------------------------------------------------

    def test_permissions_not_assigned_to_other_user(self):
        """The other_user does not receive permissions from the signal."""
        with self.captureOnCommitCallbacks(execute=True):
            project = Project.objects.create(
                title="SigIsolation",
                label="SIGISO01",
                status="ACTIVE",
                created_by=self.user,
            )
        other_perms = get_perms(self.other_user, project)
        self.assertNotIn("view_project", other_perms)
        self.assertNotIn("change_project", other_perms)
        self.assertNotIn("delete_project", other_perms)

    # ------------------------------------------------------------------
    # Signal works for other BaseModel subclasses too
    # ------------------------------------------------------------------

    def test_signal_fires_for_researcher_model(self):
        """Signal assigns permissions on any BaseModel subclass, not just Project."""
        user_for_researcher = User.objects.create_user(username="res_sig_u", password="pw")
        researcher_user = User.objects.create_user(username="res_own", password="pw")
        with self.captureOnCommitCallbacks(execute=True):
            researcher = Researcher.objects.create(
                user=researcher_user,
                academic_rank="D",
                created_by=user_for_researcher,
            )
        perms = get_perms(user_for_researcher, researcher)
        self.assertIn("view_researcher", perms)
        self.assertIn("change_researcher", perms)
        self.assertIn("delete_researcher", perms)


class ResearchGroupPermissionTest(TestCase):
    """Tests for ResearchGroup creation and permission signal."""

    def test_researchgroup_permissions_on_create(self):
        user = User.objects.create_user(username="rg_sig_u", password="pw")
        auth_group = Group.objects.create(name="RG Signal Group")
        with self.captureOnCommitCallbacks(execute=True):
            rg = ResearchGroup.objects.create(
                label="Test RG Signal",
                auth_group=auth_group,
                created_by=user,
            )
        perms = get_perms(user, rg)
        self.assertIn("view_researchgroup", perms)
        self.assertIn("change_researchgroup", perms)
        self.assertIn("delete_researchgroup", perms)
