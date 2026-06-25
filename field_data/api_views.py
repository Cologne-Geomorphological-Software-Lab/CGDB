"""REST API ViewSets for field_data models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q
from rest_framework.viewsets import ReadOnlyModelViewSet

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import QuerySet
    from rest_framework.serializers import BaseSerializer

from prototype.api_permissions import IsProjectMember
from prototype.mixins import _accessible_projects

from .models import (
    Campaign,
    ExposureType,
    Layer,
    Location,
    Sample,
    SampleType,
    StudyArea,
    Transect,
)
from .serializers import (
    CampaignSerializer,
    ExposureTypeSerializer,
    LayerSerializer,
    LocationFlatSerializer,
    LocationGeoSerializer,
    SampleSerializer,
    SampleTypeSerializer,
    StudyAreaGeoSerializer,
    TransectSerializer,
)


def _project_qs(
    user: AbstractBaseUser | AnonymousUser, qs: QuerySet
) -> QuerySet:
    """Filter a queryset by accessible projects for the given user."""
    if user.is_superuser:
        return qs
    project_ids = _accessible_projects(user).values_list("id", flat=True)
    return qs.filter(project_id__in=project_ids)


class LocationViewSet(ReadOnlyModelViewSet):
    """Paginated, filterable list of accessible locations."""

    permission_classes = [IsProjectMember]
    filterset_fields = [
        "project",
        "campaign",
        "data_source",
        "location_type",
        "exposure_type",
        "sampling",
        "study_site__study_area",
    ]
    search_fields = ["identifier", "=project__label"]
    ordering_fields = [
        "date_of_record",
        "created_at",
        "altitude",
        "identifier",
    ]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[Location]:
        """Return locations filtered to projects the user can access."""
        user = self.request.user
        qs = Location.objects.select_related(
            "project", "campaign", "study_site", "transect", "exposure_type"
        )
        if user.is_superuser:
            return qs
        project_ids = _accessible_projects(user).values_list("id", flat=True)
        return qs.filter(
            Q(project_id__in=project_ids) | Q(data_source="literature")
        )

    def get_serializer_class(self) -> type[BaseSerializer]:
        """Return GeoJSON serializer by default; flat JSON for explicit JSON format."""
        if (
            getattr(self.request, "accepted_renderer", None)
            and self.request.accepted_renderer.format == "json"
        ):
            return LocationFlatSerializer
        return LocationGeoSerializer


class CampaignViewSet(ReadOnlyModelViewSet):
    """Read-only list of campaigns scoped to accessible projects."""

    serializer_class = CampaignSerializer
    permission_classes = [IsProjectMember]
    filterset_fields = ["project"]
    search_fields = ["label"]
    ordering_fields = ["label", "date_start"]
    ordering = ["label"]

    def get_queryset(self) -> QuerySet[Campaign]:
        """Return campaigns for projects the user can access."""
        return _project_qs(
            self.request.user, Campaign.objects.select_related("project")
        )


class StudyAreaViewSet(ReadOnlyModelViewSet):
    """Read-only list of study areas scoped to accessible projects."""

    serializer_class = StudyAreaGeoSerializer
    permission_classes = [IsProjectMember]
    filterset_fields = ["project"]
    search_fields = ["label"]
    ordering = ["label"]

    def get_queryset(self) -> QuerySet[StudyArea]:
        """Return study areas for projects the user can access."""
        return _project_qs(
            self.request.user, StudyArea.objects.select_related("project")
        )


class TransectViewSet(ReadOnlyModelViewSet):
    """Read-only list of transects scoped to accessible projects."""

    serializer_class = TransectSerializer
    permission_classes = [IsProjectMember]
    filterset_fields = ["study_area", "campaign"]
    search_fields = ["identifier"]
    ordering = ["identifier"]

    def get_queryset(self) -> QuerySet[Transect]:
        """Return transects for study areas the user can access."""
        user = self.request.user
        qs = Transect.objects.select_related("study_area__project", "campaign")
        if user.is_superuser:
            return qs
        project_ids = _accessible_projects(user).values_list("id", flat=True)
        return qs.filter(study_area__project_id__in=project_ids)


class LayerViewSet(ReadOnlyModelViewSet):
    """Read-only list of stratigraphic layers scoped to accessible projects."""

    serializer_class = LayerSerializer
    permission_classes = [IsProjectMember]
    filterset_fields = ["location"]
    ordering = ["location", "depth_top"]

    def get_queryset(self) -> QuerySet[Layer]:
        """Return layers for locations the user can access."""
        user = self.request.user
        qs = Layer.objects.select_related("location__project")
        if user.is_superuser:
            return qs
        project_ids = _accessible_projects(user).values_list("id", flat=True)
        return qs.filter(
            Q(location__project_id__in=project_ids)
            | Q(location__data_source="literature")
        )


class SampleViewSet(ReadOnlyModelViewSet):
    """Read-only list of samples scoped to accessible projects."""

    serializer_class = SampleSerializer
    permission_classes = [IsProjectMember]
    filterset_fields = ["project", "location", "layer", "type"]
    search_fields = ["identifier", "igsn"]
    ordering_fields = ["identifier", "date", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[Sample]:
        """Return samples for projects the user can access."""
        user = self.request.user
        qs = Sample.objects.select_related(
            "project", "location", "layer", "type"
        )
        if user.is_superuser:
            return qs
        project_ids = _accessible_projects(user).values_list("id", flat=True)
        return qs.filter(
            Q(project_id__in=project_ids)
            | Q(location__data_source="literature")
        )


class ExposureTypeViewSet(ReadOnlyModelViewSet):
    """Lookup table — no project scoping needed."""

    queryset = ExposureType.objects.all()
    serializer_class = ExposureTypeSerializer
    ordering = ["name_en"]


class SampleTypeViewSet(ReadOnlyModelViewSet):
    """Lookup table — no project scoping needed."""

    queryset = SampleType.objects.all()
    serializer_class = SampleTypeSerializer
    ordering = ["word"]
