"""API tests for bibliography ViewSets.

bibliography is treated as a shared literature catalog (IsAuthenticated
only) — Reference.project is an optional M2M and does not gate visibility,
even for a project the requesting user is not a member of. This file
documents that decision explicitly (see ReferenceViewSetTest below).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from django.contrib.auth.models import User
from django.test import Client, TestCase
from rest_framework.test import APIClient

from bibliography.models import Author, Reference, ReferenceKeyword
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
    user: ClassVar[User]
    author: ClassVar[Author]
    keyword: ClassVar[ReferenceKeyword]
    project: ClassVar[Project]
    reference: ClassVar[Reference]
    client: _TestClient

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="bib_api_user", password="pw")
        cls.author = Author.objects.create(last_name="Doe", first_name="Jane")
        cls.keyword = ReferenceKeyword.objects.create(keyword="Loess")
        cls.project = Project.objects.create(
            title="Bibliography API Project", label="BAP01", status="ACTIVE"
        )
        cls.reference = Reference.objects.create(
            title="Aeolian deposits of the Rhine valley",
            year=2020,
            lead_author=cls.author,
            abstract="An abstract.",
            type="Paper",
        )
        cls.reference.project.add(cls.project)
        cls.reference.keywords.add(cls.keyword)

    def setUp(self) -> None:
        self.client = _make_client()
        self.client.force_authenticate(user=self.user)


class AuthorViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/authors/")
        assert resp.status_code == 200

    def test_list_contains_author(self) -> None:
        resp = self.client.get("/api/v1/authors/")
        names = [item["last_name"] for item in resp.json()["results"]]
        assert "Doe" in names

    def test_unauthenticated_returns_401_or_403(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/authors/")
        assert resp.status_code in (401, 403)


class ReferenceKeywordViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/reference-keywords/")
        assert resp.status_code == 200

    def test_list_contains_keyword(self) -> None:
        resp = self.client.get("/api/v1/reference-keywords/")
        keywords = [item["keyword"] for item in resp.json()["results"]]
        assert "Loess" in keywords


class ReferenceViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/references/")
        assert resp.status_code == 200

    def test_detail_returns_200(self) -> None:
        resp = self.client.get(f"/api/v1/references/{self.reference.pk}/")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Aeolian deposits of the Rhine valley"

    def test_reference_visible_without_project_membership(self) -> None:
        """A Reference whose project M2M points at a project the user is not
        a member of is still visible — bibliography is a shared catalog,
        not project-scoped data (see F4's design decision)."""
        other_user = User.objects.create_user(username="bib_no_perm", password="pw")
        client = _make_client()
        client.force_authenticate(user=other_user)
        resp = client.get(f"/api/v1/references/{self.reference.pk}/")
        assert resp.status_code == 200

    def test_filter_by_type(self) -> None:
        resp = self.client.get("/api/v1/references/?type=Paper")
        titles = [item["title"] for item in resp.json()["results"]]
        assert "Aeolian deposits of the Rhine valley" in titles
