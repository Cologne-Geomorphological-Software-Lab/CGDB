"""Tests for ProjectAdmin._sync_member_permissions().

Tests the member ↔ Guardian-permission synchronisation that runs after
a project is saved with a changed members M2M field.

We test _sync_member_permissions() directly rather than going through
save_related() so we don't have to construct real admin formsets.
The method only reads project.members and ProjectUserObjectPermission —
both are real DB objects — so the tests are faithful integration tests.
"""
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase

from guardian.shortcuts import assign_perm, get_perms

from prototype.admin import ProjectAdmin, _MEMBER_PERMS
from prototype.models import Project


def _make_admin():
    return ProjectAdmin(Project, AdminSite())


class SyncMemberPermissionsGrantTest(TestCase):
    """Adding users to members grants the three member permissions."""

    @classmethod
    def setUpTestData(cls):
        cls.creator = User.objects.create_user(username="adm_creator", password="pw")
        cls.member = User.objects.create_user(username="adm_member", password="pw")

    def setUp(self):
        self.project = Project.objects.create(
            title="Admin Sync Test", label="AST01", status="ACTIVE",
            created_by=self.creator,
        )

    def test_new_member_receives_view_permission(self):
        self.project.members.add(self.member)
        _make_admin()._sync_member_permissions(self.project)
        self.assertIn("view_project", get_perms(self.member, self.project))

    def test_new_member_receives_add_permission(self):
        self.project.members.add(self.member)
        _make_admin()._sync_member_permissions(self.project)
        self.assertIn("add_project", get_perms(self.member, self.project))

    def test_new_member_receives_change_permission(self):
        self.project.members.add(self.member)
        _make_admin()._sync_member_permissions(self.project)
        self.assertIn("change_project", get_perms(self.member, self.project))

    def test_new_member_does_not_receive_delete_permission(self):
        self.project.members.add(self.member)
        _make_admin()._sync_member_permissions(self.project)
        self.assertNotIn("delete_project", get_perms(self.member, self.project))

    def test_multiple_members_all_receive_permissions(self):
        extra = User.objects.create_user(username="adm_extra", password="pw")
        self.project.members.add(self.member, extra)
        _make_admin()._sync_member_permissions(self.project)
        for user in (self.member, extra):
            perms = get_perms(user, self.project)
            for perm in _MEMBER_PERMS:
                self.assertIn(perm, perms, msg=f"{user} missing {perm}")


class SyncMemberPermissionsRevokeTest(TestCase):
    """Removing users from members revokes the three member permissions."""

    @classmethod
    def setUpTestData(cls):
        cls.creator = User.objects.create_user(username="adm_rev_creator", password="pw")
        cls.ex_member = User.objects.create_user(username="adm_ex_member", password="pw")

    def setUp(self):
        self.project = Project.objects.create(
            title="Admin Revoke Test", label="ART01", status="ACTIVE",
            created_by=self.creator,
        )
        for perm in _MEMBER_PERMS:
            assign_perm(perm, self.ex_member, self.project)

    def test_removed_member_loses_view_permission(self):
        # ex_member not in members M2M → sync should revoke
        _make_admin()._sync_member_permissions(self.project)
        self.assertNotIn("view_project", get_perms(self.ex_member, self.project))

    def test_removed_member_loses_add_permission(self):
        _make_admin()._sync_member_permissions(self.project)
        self.assertNotIn("add_project", get_perms(self.ex_member, self.project))

    def test_removed_member_loses_change_permission(self):
        _make_admin()._sync_member_permissions(self.project)
        self.assertNotIn("change_project", get_perms(self.ex_member, self.project))

    def test_removed_member_explicit_delete_perm_is_not_touched(self):
        """delete_project is outside _MEMBER_PERMS; sync never removes it."""
        assign_perm("delete_project", self.ex_member, self.project)
        _make_admin()._sync_member_permissions(self.project)
        self.assertIn("delete_project", get_perms(self.ex_member, self.project))


class SyncMemberPermissionsCreatorTest(TestCase):
    """The creator's permissions are never revoked by the sync."""

    @classmethod
    def setUpTestData(cls):
        cls.creator = User.objects.create_user(username="adm_cre_creator", password="pw")

    def setUp(self):
        self.project = Project.objects.create(
            title="Creator Guard Test", label="CGT01", status="ACTIVE",
            created_by=self.creator,
        )
        for perm in _MEMBER_PERMS:
            assign_perm(perm, self.creator, self.project)

    def test_creator_keeps_view_permission_even_when_not_in_members(self):
        # creator is NOT in members M2M
        _make_admin()._sync_member_permissions(self.project)
        self.assertIn("view_project", get_perms(self.creator, self.project))

    def test_creator_keeps_add_permission_even_when_not_in_members(self):
        _make_admin()._sync_member_permissions(self.project)
        self.assertIn("add_project", get_perms(self.creator, self.project))

    def test_creator_keeps_change_permission_even_when_not_in_members(self):
        _make_admin()._sync_member_permissions(self.project)
        self.assertIn("change_project", get_perms(self.creator, self.project))


class SyncMemberPermissionsIdempotentTest(TestCase):
    """Calling sync twice has the same effect as calling it once."""

    @classmethod
    def setUpTestData(cls):
        cls.creator = User.objects.create_user(username="adm_idem_creator", password="pw")
        cls.member = User.objects.create_user(username="adm_idem_member", password="pw")

    def setUp(self):
        self.project = Project.objects.create(
            title="Idempotent Test", label="IDM01", status="ACTIVE",
            created_by=self.creator,
        )
        self.project.members.add(self.member)

    def test_second_sync_does_not_raise_or_duplicate(self):
        admin = _make_admin()
        admin._sync_member_permissions(self.project)
        admin._sync_member_permissions(self.project)
        perms = get_perms(self.member, self.project)
        for perm in _MEMBER_PERMS:
            self.assertIn(perm, perms)
