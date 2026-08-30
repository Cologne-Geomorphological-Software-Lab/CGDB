"""Tests for BulkTagActionMixin's bulk add/remove tag admin actions.

Architecture-review fix (F11): _bulk_tag_action used to loop
`obj.tags.add(*tags)`/`.remove(*tags)` once per selected object -- O(N)
M2M round-trips for an N-object admin selection. It now writes directly
through the "tags" M2M's auto-generated through model in one
bulk_create()/delete() call instead. These tests cover correctness of that
rewrite (add/remove/idempotency/query-count), not just that the action
still "looks the same" from the outside.
"""

from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from field_data.admin import LocationAdmin
from field_data.models import Location, Tag
from prototype.models import Project

if TYPE_CHECKING:
    from prototype.mixins import AuthenticatedHttpRequest


class BulkTagActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="bulktag_admin", password="pw", email="bt@test.com"
        )
        cls.project = Project.objects.create(
            title="Bulk Tag Project", label="BTP01", status="ACTIVE"
        )
        ct = ContentType.objects.get_for_model(Location)
        cls.tag_a = Tag.objects.create(
            word="alpha", content_type=ct, project=cls.project
        )
        cls.tag_b = Tag.objects.create(
            word="beta", content_type=ct, project=cls.project
        )
        cls.loc1 = Location.objects.create(
            identifier="BT_LOC1", data_source="internal", project=cls.project
        )
        cls.loc2 = Location.objects.create(
            identifier="BT_LOC2", data_source="internal", project=cls.project
        )

    def setUp(self):
        self.site = AdminSite()
        self.admin = LocationAdmin(Location, self.site)
        self.factory = RequestFactory()

    def _post(self, tag_pks) -> "AuthenticatedHttpRequest":
        data = {
            "_apply_tag_action": "1",
            "tags": [str(pk) for pk in tag_pks],
        }
        request = self.factory.post("/", data)
        request.user = self.superuser
        request._messages = MagicMock()  # pyright: ignore[reportAttributeAccessIssue]  # messages middleware attr; test bypasses the middleware and sets it directly
        return cast("AuthenticatedHttpRequest", request)

    def test_add_tags_applies_to_every_selected_object(self):
        request = self._post([self.tag_a.pk, self.tag_b.pk])
        qs = Location.objects.filter(pk__in=[self.loc1.pk, self.loc2.pk])
        self.admin.add_tags_to_selected(request, qs)
        self.assertEqual(set(self.loc1.tags.all()), {self.tag_a, self.tag_b})
        self.assertEqual(set(self.loc2.tags.all()), {self.tag_a, self.tag_b})

    def test_add_tags_is_idempotent_for_already_tagged_objects(self):
        self.loc1.tags.add(self.tag_a)
        request = self._post([self.tag_a.pk, self.tag_b.pk])
        qs = Location.objects.filter(pk__in=[self.loc1.pk, self.loc2.pk])
        # Must not raise IntegrityError on the already-tagged (loc1, tag_a)
        # combination -- bulk_create(ignore_conflicts=True) must behave the
        # same as the old .add()'s idempotency.
        self.admin.add_tags_to_selected(request, qs)
        self.assertEqual(set(self.loc1.tags.all()), {self.tag_a, self.tag_b})
        self.assertEqual(set(self.loc2.tags.all()), {self.tag_a, self.tag_b})

    def test_remove_tags_removes_from_every_selected_object(self):
        self.loc1.tags.add(self.tag_a, self.tag_b)
        self.loc2.tags.add(self.tag_a, self.tag_b)
        request = self._post([self.tag_a.pk])
        qs = Location.objects.filter(pk__in=[self.loc1.pk, self.loc2.pk])
        self.admin.remove_tags_from_selected(request, qs)
        self.assertEqual(set(self.loc1.tags.all()), {self.tag_b})
        self.assertEqual(set(self.loc2.tags.all()), {self.tag_b})

    def test_remove_tags_leaves_untagged_objects_unaffected(self):
        self.loc1.tags.add(self.tag_a)
        request = self._post([self.tag_a.pk])
        qs = Location.objects.filter(pk__in=[self.loc1.pk, self.loc2.pk])
        self.admin.remove_tags_from_selected(request, qs)  # loc2 was never tagged
        self.assertEqual(set(self.loc1.tags.all()), set())
        self.assertEqual(set(self.loc2.tags.all()), set())

    def test_unselected_objects_are_never_touched(self):
        request = self._post([self.tag_a.pk])
        qs = Location.objects.filter(pk=self.loc1.pk)  # loc2 not selected
        self.admin.add_tags_to_selected(request, qs)
        self.assertEqual(set(self.loc1.tags.all()), {self.tag_a})
        self.assertEqual(set(self.loc2.tags.all()), set())

    def test_add_tags_query_count_does_not_scale_with_selection_size(self):
        """A handful of fixed queries (materialize queryset, bulk_create,
        message), not one add() round-trip per object -- 10 objects must
        not cost more queries than tagging a single object."""
        locations = [
            Location.objects.create(
                identifier=f"BT_LOC_MANY_{i}",
                data_source="internal",
                project=self.project,
            )
            for i in range(10)
        ]
        try:
            many_request = self._post([self.tag_a.pk])
            many_qs = Location.objects.filter(
                pk__in=[loc.pk for loc in locations]
            )
            with CaptureQueriesContext(connection) as many_ctx:
                self.admin.add_tags_to_selected(many_request, many_qs)

            single_request = self._post([self.tag_b.pk])
            single_qs = Location.objects.filter(pk=self.loc1.pk)
            with CaptureQueriesContext(connection) as single_ctx:
                self.admin.add_tags_to_selected(single_request, single_qs)

            assert len(many_ctx) == len(single_ctx)
        finally:
            Location.objects.filter(
                pk__in=[loc.pk for loc in locations]
            ).delete()
