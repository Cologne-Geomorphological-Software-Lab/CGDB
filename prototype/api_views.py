"""REST API ViewSets for the prototype app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.viewsets import ReadOnlyModelViewSet

if TYPE_CHECKING:
    from django.db.models import QuerySet

from prototype.mixins import _addable_projects

from .models import Project
from .serializers import ProjectSerializer


class ThrottledObtainAuthToken(ObtainAuthToken):
    """DRF's token-auth login view, with its own stricter throttle scope.

    The global DEFAULT_THROTTLE_RATES["anon"] (see REST_FRAMEWORK in
    settings.py) is meant for general anonymous API access; a login
    endpoint needs a much tighter limit specifically to slow down
    credential-stuffing/brute-force attempts, so it gets its own "login"
    scope instead of sharing the general anonymous rate.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class ProjectViewSet(ReadOnlyModelViewSet):
    """Read-only list of projects the user may add data to.

    Scoped to add_project (not view_project) — this exists specifically to
    populate the map dashboard's "new StudyArea/Transect" project picker,
    not as a general-purpose project listing endpoint.
    """

    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ["title"]
    ordering = ["title"]

    def get_queryset(self) -> QuerySet[Project]:
        """Return projects the user may add data to."""
        user = self.request.user
        if user.is_superuser:
            return Project.objects.all()
        return _addable_projects(user)
