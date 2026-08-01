"""REST API ViewSets for bibliography models.

Treated as a shared literature catalog, not project-scoped data — every
viewset here is IsAuthenticated-only (see ReferenceSerializer's docstring
for why Reference.project's M2M doesn't gate visibility).
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Author, Reference, ReferenceKeyword
from .serializers import (
    AuthorSerializer,
    ReferenceKeywordSerializer,
    ReferenceSerializer,
)


class AuthorViewSet(ReadOnlyModelViewSet):
    """Read-only list of authors."""

    queryset = Author.objects.select_related("user")
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["last_name", "first_name"]
    ordering = ["last_name", "first_name"]


class ReferenceKeywordViewSet(ReadOnlyModelViewSet):
    """Read-only list of reference keywords."""

    queryset = ReferenceKeyword.objects.all()
    serializer_class = ReferenceKeywordSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["keyword", "keyword_ger"]
    ordering = ["keyword"]


class ReferenceViewSet(ReadOnlyModelViewSet):
    """Read-only list of literature references."""

    queryset = Reference.objects.select_related(
        "lead_author"
    ).prefetch_related("second_author", "supervisor", "project", "keywords")
    serializer_class = ReferenceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["type", "year", "lead_author", "published"]
    search_fields = ["title", "abstract", "journal", "doi"]
    ordering_fields = ["year", "title"]
    ordering = ["-year", "title"]
