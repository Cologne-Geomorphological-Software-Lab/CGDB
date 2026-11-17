"""API tests for analysis ViewSets.

Covers the three permission-scoping patterns used across the app's 15
viewsets (see F4 in the architecture-audit plan):
- sample-scoped (GrainSizeViewSet): permission/queryset resolved via .sample.project
- catalog / no scoping (AlgorithmViewSet): IsAuthenticated only
- nested two-hop (PollenCountViewSet): resolved via .counting.sample.project
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar, cast

from django.contrib.auth.models import User
from django.test import Client, TestCase
from guardian.shortcuts import assign_perm
from rest_framework.test import APIClient

from analysis.models import (
    Algorithm,
    Counting,
    GrainSize,
    Pollen,
    PollenCount,
    RadiocarbonDating,
)
from field_data.models import Location, Sample
from prototype.models import Project
from prototype.tests.roles import give_role

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
        give_role(cls.member)
        cls.non_member = User.objects.create_user(
            username="analysis_non_member", password="pw"
        )
        give_role(cls.non_member)
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


class RawMeasurementSerializerTest(_BaseApiTest):
    """The serializer rejects samples of another project (#244)."""

    def test_sample_of_another_project_is_rejected(self) -> None:
        from analysis.serializers import RawMeasurementSerializer
        from laboratory.models import Device
        from prototype.models import Researcher

        other_location = Location.objects.create(
            identifier="AAP_LOC_B",
            data_source="internal",
            project=self.other_project,
        )
        other_sample = Sample.objects.create(
            identifier="AAP_S_B",
            project=self.other_project,
            location=other_location,
        )
        device = Device.objects.create(name="AAP Device")
        researcher = Researcher.objects.create(
            user=User.objects.create_user(username="aap_researcher"),
            academic_rank="D",
            position="WiMa",
        )
        serializer = RawMeasurementSerializer(
            data={
                "project": self.project.pk,
                "sample": [self.sample.pk, other_sample.pk],
                "device": device.pk,
                "researcher": researcher.pk,
            }
        )
        assert not serializer.is_valid()
        errors = str(serializer.errors)
        assert "sample" in errors
        assert "AAP_S_B" in errors


class RadiocarbonDatingViewSetTest(_BaseApiTest):
    """The serializer exposes the quality assessment (#283)."""

    dating: ClassVar[RadiocarbonDating]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.dating = RadiocarbonDating.objects.create(
            sample=cls.sample,
            lab="Poznań",
            lab_id="Poz-283",
            age=Decimal("12.500"),
            age_error=Decimal("0.050"),
            data_quality="rejected",
            quality_note="Contaminated by modern carbon.",
        )

    def test_detail_includes_data_quality_fields(self) -> None:
        resp = self.client.get(
            f"/api/v1/radiocarbon-datings/{self.dating.pk}/"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data_quality"] == "rejected"
        assert body["quality_note"] == "Contaminated by modern carbon."

    def test_detail_includes_age_error(self) -> None:
        """The uncertainty travels with the age (#194)."""
        resp = self.client.get(
            f"/api/v1/radiocarbon-datings/{self.dating.pk}/"
        )
        body = resp.json()
        assert Decimal(str(body["age"])) == Decimal("12.500")
        assert Decimal(str(body["age_error"])) == Decimal("0.050")

    def test_list_includes_data_quality_fields(self) -> None:
        resp = self.client.get("/api/v1/radiocarbon-datings/")
        assert resp.status_code == 200
        (item,) = [
            r for r in resp.json()["results"] if r["id"] == self.dating.pk
        ]
        assert item["data_quality"] == "rejected"
        assert "quality_note" in item


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
