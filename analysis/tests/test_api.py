"""API tests for analysis ViewSets.

Covers the three permission-scoping patterns used across the app's 15
viewsets (see F4 in the architecture-audit plan):
- sample-scoped (GrainSizeViewSet): permission/queryset resolved via .sample.project
- catalog / no scoping (AlgorithmViewSet): IsAuthenticated only
- nested two-hop (PollenCountViewSet): resolved via .counting.sample.project
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from django.contrib.auth.models import User
from django.test import Client, TestCase
from guardian.shortcuts import assign_perm
from rest_framework.test import APIClient

from analysis.models import Algorithm, Counting, GrainSize, Pollen, PollenCount
from field_data.models import Location, Sample
from prototype.models import Project

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

    class _TestClient(Client):
        """Narrow, correctly-typed view of APIClient for use in tests."""

        def force_authenticate(self, user: object = ...) -> None: ...
        def get(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...


def _make_client() -> _TestClient:
    """Return a new APIClient, cast to the correctly-typed class above."""
    return cast("_TestClient", APIClient())


class _BaseApiTest(TestCase):
    member: ClassVar[User]
    non_member: ClassVar[User]
    project: ClassVar[Project]
    other_project: ClassVar[Project]
    sample: ClassVar[Sample]
    client: _TestClient

    @classmethod
    def setUpTestData(cls) -> None:
        cls.member = User.objects.create_user(
            username="analysis_member", password="pw"
        )
        cls.non_member = User.objects.create_user(
            username="analysis_non_member", password="pw"
        )
        cls.project = Project.objects.create(
            title="Analysis API Project", label="AAP01", status="ACTIVE"
        )
        cls.other_project = Project.objects.create(
            title="Other Project", label="AAP02", status="ACTIVE"
        )
        assign_perm("view_project", cls.member, cls.project)

        location = Location.objects.create(
            identifier="AAP_LOC", data_source="internal", project=cls.project
        )
        cls.sample = Sample.objects.create(
            identifier="AAP_S01", project=cls.project, location=location
        )

    def setUp(self) -> None:
        self.client = _make_client()
        self.client.force_authenticate(user=self.member)


class GrainSizeViewSetTest(_BaseApiTest):
    """Sample-scoped permission/queryset pattern (SampleScopedPermission)."""

    grain_size: ClassVar[GrainSize]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.grain_size = GrainSize.objects.create(
            sample=cls.sample, method="L", measured_data=None
        )

    def test_member_sees_grain_size(self) -> None:
        resp = self.client.get("/api/v1/grain-sizes/")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["results"]]
        assert self.grain_size.pk in ids

    def test_member_can_retrieve_detail(self) -> None:
        resp = self.client.get(f"/api/v1/grain-sizes/{self.grain_size.pk}/")
        assert resp.status_code == 200
        assert resp.json()["method"] == "L"

    def test_non_member_detail_returns_403_or_404(self) -> None:
        client = _make_client()
        client.force_authenticate(user=self.non_member)
        resp = client.get(f"/api/v1/grain-sizes/{self.grain_size.pk}/")
        assert resp.status_code in (403, 404)

    def test_unauthenticated_returns_401_or_403(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/grain-sizes/")
        assert resp.status_code in (401, 403)


class AlgorithmViewSetTest(_BaseApiTest):
    """Catalog pattern — no project scoping (IsAuthenticated only)."""

    algorithm: ClassVar[Algorithm]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.algorithm = Algorithm.objects.create(
            name="Baseline Correction",
            version="1.0",
            programming_language="Python",
        )

    def test_non_member_still_sees_algorithm(self) -> None:
        """A user with no project permissions at all still sees catalog rows."""
        client = _make_client()
        client.force_authenticate(user=self.non_member)
        resp = client.get("/api/v1/algorithms/")
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["results"]]
        assert "Baseline Correction" in names

    def test_unauthenticated_returns_401_or_403(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/algorithms/")
        assert resp.status_code in (401, 403)


class PollenCountViewSetTest(_BaseApiTest):
    """Nested two-hop pattern (CountingScopedPermission via counting.sample.project)."""

    pollen_count: ClassVar[PollenCount]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        counting = Counting.objects.create(sample=cls.sample, type="Percent")
        pollen = Pollen.objects.create(name="Betula", token="BET")
        cls.pollen_count = PollenCount.objects.create(
            counting=counting, pollen=pollen, number=42
        )

    def test_member_sees_pollen_count(self) -> None:
        resp = self.client.get("/api/v1/pollen-counts/")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["results"]]
        assert self.pollen_count.pk in ids

    def test_member_can_retrieve_detail(self) -> None:
        resp = self.client.get(f"/api/v1/pollen-counts/{self.pollen_count.pk}/")
        assert resp.status_code == 200
        assert resp.json()["number"] == 42

    def test_non_member_detail_returns_403_or_404(self) -> None:
        client = _make_client()
        client.force_authenticate(user=self.non_member)
        resp = client.get(f"/api/v1/pollen-counts/{self.pollen_count.pk}/")
        assert resp.status_code in (403, 404)
