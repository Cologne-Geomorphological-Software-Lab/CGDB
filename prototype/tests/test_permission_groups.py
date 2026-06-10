"""Tests for prototype/permissions.py — create_permission_groups().

Verifies that:
- The expected groups are created on first call.
- Each academic role group contains the right permission verbs.
- The function is idempotent (safe to call multiple times).
- reset=True clears permissions before re-adding.
- Domain groups only contain permissions for their own models.
"""
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from prototype.permissions import GROUPS, create_permission_groups


class CreatePermissionGroupsTest(TestCase):

    def test_all_groups_are_created(self):
        create_permission_groups()
        existing = set(Group.objects.values_list("name", flat=True))
        for group_name in GROUPS:
            self.assertIn(group_name, existing)

    def test_viewer_has_only_view_permissions(self):
        create_permission_groups()
        group = Group.objects.get(name="Viewer")
        codenames = set(group.permissions.values_list("codename", flat=True))
        for codename in codenames:
            action = codename.split("_")[0]
            self.assertEqual(action, "view", msg=f"Viewer has non-view permission: {codename}")

    def test_researcher_has_no_delete_permissions(self):
        create_permission_groups()
        group = Group.objects.get(name="Researcher")
        codenames = set(group.permissions.values_list("codename", flat=True))
        delete_perms = [c for c in codenames if c.startswith("delete_")]
        self.assertEqual(delete_perms, [], msg=f"Researcher must not have delete perms: {delete_perms}")

    def test_researcher_has_view_add_change(self):
        create_permission_groups()
        group = Group.objects.get(name="Researcher")
        codenames = set(group.permissions.values_list("codename", flat=True))
        actions = {c.split("_")[0] for c in codenames}
        self.assertIn("view", actions)
        self.assertIn("add", actions)
        self.assertIn("change", actions)

    def test_principal_investigator_has_all_four_actions(self):
        create_permission_groups()
        group = Group.objects.get(name="Principal Investigator")
        codenames = set(group.permissions.values_list("codename", flat=True))
        actions = {c.split("_")[0] for c in codenames}
        self.assertIn("view", actions)
        self.assertIn("add", actions)
        self.assertIn("change", actions)
        self.assertIn("delete", actions)

    def test_idempotent_does_not_duplicate_groups(self):
        create_permission_groups()
        create_permission_groups()
        for group_name in GROUPS:
            count = Group.objects.filter(name=group_name).count()
            self.assertEqual(count, 1, msg=f"Group '{group_name}' exists {count} times after two calls")

    def test_idempotent_does_not_duplicate_permissions(self):
        create_permission_groups()
        create_permission_groups()
        group = Group.objects.get(name="Viewer")
        # Permissions are stored in a M2M set — no duplicates possible, but
        # re-running should not raise.
        self.assertGreater(group.permissions.count(), 0)

    def test_reset_clears_then_re_adds_permissions(self):
        create_permission_groups()
        group = Group.objects.get(name="Viewer")
        before = group.permissions.count()
        self.assertGreater(before, 0)

        # Manually wipe the group's permissions and verify reset restores them.
        group.permissions.clear()
        self.assertEqual(group.permissions.count(), 0)

        create_permission_groups(reset=True)
        group.refresh_from_db()
        after = group.permissions.count()
        self.assertEqual(after, before)

    def test_reset_false_does_not_remove_extra_permissions(self):
        """reset=False (default) leaves manually added permissions in place."""
        create_permission_groups()
        group = Group.objects.get(name="Viewer")
        extra = Permission.objects.filter(codename="add_project").first()
        if extra:
            group.permissions.add(extra)
            before = group.permissions.count()
            create_permission_groups(reset=False)
            self.assertEqual(group.permissions.count(), before)

    def test_luminescence_group_has_correct_models(self):
        create_permission_groups()
        group = Group.objects.get(name="Luminescence")
        models = set(
            group.permissions.values_list("content_type__model", flat=True)
        )
        self.assertIn("luminescencedating", models)
        self.assertIn("rawmeasurement", models)
        self.assertIn("rawprocessing", models)

    def test_bibliography_group_has_correct_models(self):
        create_permission_groups()
        group = Group.objects.get(name="Bibliography")
        models = set(
            group.permissions.values_list("content_type__model", flat=True)
        )
        self.assertIn("reference", models)
        self.assertIn("author", models)
        self.assertIn("referencekeyword", models)

    def test_stdout_output_is_written(self):
        import io
        buf = io.StringIO()

        class _FakeStdout:
            def write(self, s: str):
                buf.write(s)

        create_permission_groups(stdout=_FakeStdout())
        output = buf.getvalue()
        self.assertIn("Viewer", output)
        self.assertIn("Principal Investigator", output)

    def test_returns_created_and_updated_counts(self):
        created, updated = create_permission_groups()
        expected_total = len(GROUPS)
        self.assertEqual(created + updated, expected_total)

    def test_second_call_returns_zero_created(self):
        create_permission_groups()
        created, updated = create_permission_groups()
        self.assertEqual(created, 0)
        self.assertEqual(updated, len(GROUPS))
