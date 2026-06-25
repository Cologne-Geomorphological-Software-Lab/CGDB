"""REST API ViewSets for geodata models."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Geomorphon, Landform, WorldCover
from .serializers import (
    GeomorphonGeoSerializer,
    LandformGeoSerializer,
    WorldCoverGeoSerializer,
)


class GeomorphonViewSet(ReadOnlyModelViewSet):
    """Read-only API for geomorphon terrain form polygons."""

    queryset = Geomorphon.objects.select_related("study_area")
    serializer_class = GeomorphonGeoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["geomorphon_class", "study_area"]
    search_fields = ["source"]
    ordering_fields = ["geomorphon_class", "created_at"]
    ordering = ["geomorphon_class"]


class LandformViewSet(ReadOnlyModelViewSet):
    """Read-only API for Murphy Landform region polygons."""

    queryset = Landform.objects.all()
    serializer_class = LandformGeoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["continent", "murphy_code"]
    search_fields = [
        "name_str",
        "brid_nam",
        "murphy_code",
        "division",
        "province",
    ]
    ordering_fields = ["continent", "division", "province"]
    ordering = ["continent", "division"]


class WorldCoverViewSet(ReadOnlyModelViewSet):
    """Read-only API for ESA WorldCover land cover polygons."""

    queryset = WorldCover.objects.all()
    serializer_class = WorldCoverGeoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["landcover_class", "year"]
    search_fields = ["source"]
    ordering_fields = ["landcover_class", "year"]
    ordering = ["landcover_class"]
