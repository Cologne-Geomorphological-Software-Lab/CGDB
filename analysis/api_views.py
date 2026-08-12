"""REST API ViewSets for analysis models.

Permission/scoping follows the model's path to its owning Project (see the
architecture-audit plan, F4): models with a direct .sample FK use
SampleScopedPermission; models nested further use the matching
ProjectPathPermission subclass; models with no project relation at all
(lookup/catalog tables) use plain IsAuthenticated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import QuerySet

from prototype.api_permissions import (
    CountingScopedPermission,
    IsProjectMember,
    MeasurementScopedPermission,
    RawMeasurementScopedPermission,
    SampleScopedPermission,
)
from prototype.mixins import _accessible_projects

from .models import (
    Algorithm,
    CosmogenicNuclideDating,
    Counting,
    GenericMeasurement,
    GrainSize,
    LuminescenceDating,
    MeasurementSeries,
    MicroXRFElementMap,
    MicroXRFMeasurement,
    Parameter,
    Pollen,
    PollenCount,
    RadiocarbonDating,
    RawMeasurement,
    RawProcessing,
)
from .serializers import (
    AlgorithmSerializer,
    CosmogenicNuclideDatingSerializer,
    CountingSerializer,
    GenericMeasurementSerializer,
    GrainSizeSerializer,
    LuminescenceDatingSerializer,
    MeasurementSeriesSerializer,
    MicroXRFElementMapSerializer,
    MicroXRFMeasurementSerializer,
    ParameterSerializer,
    PollenCountSerializer,
    PollenSerializer,
    RadiocarbonDatingSerializer,
    RawMeasurementSerializer,
    RawProcessingSerializer,
)


def _project_qs(
    user: AbstractBaseUser | AnonymousUser, qs: QuerySet, field: str
) -> QuerySet:
    """Filter a queryset by accessible projects, reached via *field* (e.g. "project", "sample__project")."""
    if getattr(user, "is_superuser", False):
        return qs
    project_ids = _accessible_projects(user).values_list("id", flat=True)
    return qs.filter(**{f"{field}__in": project_ids})


class AlgorithmViewSet(ReadOnlyModelViewSet):
    """Lookup table — no project scoping needed."""

    queryset = Algorithm.objects.all()
    serializer_class = AlgorithmSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["programming_language"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "version"]
    ordering = ["name"]


class RawMeasurementViewSet(ReadOnlyModelViewSet):
    """Read-only list of raw measurement uploads, scoped to accessible projects."""

    serializer_class = RawMeasurementSerializer
    permission_classes = [IsProjectMember]
    filterset_fields = ["project", "device", "researcher"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[RawMeasurement]:
        """Return raw measurements for projects the user can access."""
        qs = RawMeasurement.objects.select_related(
            "project", "device", "accessories", "researcher"
        )
        return _project_qs(self.request.user, qs, "project_id")


class RawProcessingViewSet(ReadOnlyModelViewSet):
    """Read-only list of processed-data records, scoped via raw_measurement.project."""

    serializer_class = RawProcessingSerializer
    permission_classes = [RawMeasurementScopedPermission]
    filterset_fields = ["raw_measurement", "processed_by"]
    ordering_fields = ["processing_date"]
    ordering = ["-processing_date"]

    def get_queryset(self) -> QuerySet[RawProcessing]:
        """Return processed-data records for projects the user can access."""
        qs = RawProcessing.objects.select_related(
            "raw_measurement__project", "processed_by"
        )
        return _project_qs(
            self.request.user, qs, "raw_measurement__project_id"
        )


class CountingViewSet(ReadOnlyModelViewSet):
    """Read-only list of paleobotany counting events, scoped via sample.project."""

    serializer_class = CountingSerializer
    permission_classes = [SampleScopedPermission]
    filterset_fields = ["sample", "type"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[Counting]:
        """Return counting events for projects the user can access."""
        qs = Counting.objects.select_related("sample__project")
        return _project_qs(self.request.user, qs, "sample__project_id")


class PollenViewSet(ReadOnlyModelViewSet):
    """Lookup table — no project scoping needed."""

    queryset = Pollen.objects.all()
    serializer_class = PollenSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "name_en", "name_german", "name_nor", "token"]
    ordering_fields = ["name", "token"]
    ordering = ["name"]


class PollenCountViewSet(ReadOnlyModelViewSet):
    """Read-only list of pollen counts, scoped via counting.sample.project."""

    serializer_class = PollenCountSerializer
    permission_classes = [CountingScopedPermission]
    filterset_fields = ["counting", "pollen"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[PollenCount]:
        """Return pollen counts for projects the user can access."""
        qs = PollenCount.objects.select_related(
            "counting__sample__project", "pollen"
        )
        return _project_qs(
            self.request.user, qs, "counting__sample__project_id"
        )


class LuminescenceDatingViewSet(ReadOnlyModelViewSet):
    """Read-only list of luminescence dating results, scoped via sample.project."""

    serializer_class = LuminescenceDatingSerializer
    permission_classes = [SampleScopedPermission]
    filterset_fields = ["sample", "mineral", "dating_approach", "published"]
    search_fields = ["laboratory_id", "sample_id_cll"]
    ordering_fields = ["luminescence_age", "year_of_publication"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[LuminescenceDating]:
        """Return luminescence dating results for projects the user can access."""
        qs = LuminescenceDating.objects.select_related("sample__project")
        return _project_qs(self.request.user, qs, "sample__project_id")


class RadiocarbonDatingViewSet(ReadOnlyModelViewSet):
    """Read-only list of radiocarbon dating results, scoped via sample.project."""

    serializer_class = RadiocarbonDatingSerializer
    permission_classes = [SampleScopedPermission]
    filterset_fields = ["sample", "lab"]
    search_fields = ["lab_id"]
    ordering_fields = ["age"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[RadiocarbonDating]:
        """Return radiocarbon dating results for projects the user can access."""
        qs = RadiocarbonDating.objects.select_related("sample__project")
        return _project_qs(self.request.user, qs, "sample__project_id")


class CosmogenicNuclideDatingViewSet(ReadOnlyModelViewSet):
    """Read-only list of cosmogenic nuclide dating results, scoped via sample.project."""

    serializer_class = CosmogenicNuclideDatingSerializer
    permission_classes = [SampleScopedPermission]
    filterset_fields = ["sample", "nuclide", "mineral", "dating_approach"]
    search_fields = ["lab_id"]
    ordering_fields = ["exposure_age", "burial_age"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[CosmogenicNuclideDating]:
        """Return cosmogenic nuclide dating results for projects the user can access."""
        qs = CosmogenicNuclideDating.objects.select_related("sample__project")
        return _project_qs(self.request.user, qs, "sample__project_id")


class ParameterViewSet(ReadOnlyModelViewSet):
    """Lookup table — no project scoping needed."""

    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["unit"]
    search_fields = ["name", "token"]
    ordering_fields = ["name", "token"]
    ordering = ["name"]


class MeasurementSeriesViewSet(ReadOnlyModelViewSet):
    """Lookup table — no project scoping needed."""

    queryset = MeasurementSeries.objects.all()
    serializer_class = MeasurementSeriesSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ["datetime"]
    ordering = ["-datetime"]


class GenericMeasurementViewSet(ReadOnlyModelViewSet):
    """Read-only list of generic measurements, scoped via sample.project."""

    serializer_class = GenericMeasurementSerializer
    permission_classes = [SampleScopedPermission]
    filterset_fields = ["sample", "method", "parameter"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[GenericMeasurement]:
        """Return generic measurements for projects the user can access."""
        qs = GenericMeasurement.objects.select_related(
            "sample__project", "method", "parameter"
        )
        return _project_qs(self.request.user, qs, "sample__project_id")


class GrainSizeViewSet(ReadOnlyModelViewSet):
    """Read-only list of grain size measurements, scoped via sample.project."""

    serializer_class = GrainSizeSerializer
    permission_classes = [SampleScopedPermission]
    filterset_fields = ["sample", "method"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[GrainSize]:
        """Return grain size measurements for projects the user can access."""
        qs = GrainSize.objects.select_related("sample__project")
        return _project_qs(self.request.user, qs, "sample__project_id")


class MicroXRFMeasurementViewSet(ReadOnlyModelViewSet):
    """Read-only list of MicroXRF measurements, scoped via sample.project."""

    serializer_class = MicroXRFMeasurementSerializer
    permission_classes = [SampleScopedPermission]
    filterset_fields = ["sample", "method"]
    ordering_fields = ["measurement_date"]
    ordering = ["-measurement_date"]

    def get_queryset(self) -> QuerySet[MicroXRFMeasurement]:
        """Return MicroXRF measurements for projects the user can access."""
        qs = MicroXRFMeasurement.objects.select_related(
            "sample__project", "method"
        )
        return _project_qs(self.request.user, qs, "sample__project_id")


class MicroXRFElementMapViewSet(ReadOnlyModelViewSet):
    """Read-only list of MicroXRF element maps, scoped via measurement.sample.project."""

    serializer_class = MicroXRFElementMapSerializer
    permission_classes = [MeasurementScopedPermission]
    filterset_fields = ["measurement", "element"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[MicroXRFElementMap]:
        """Return MicroXRF element maps for projects the user can access."""
        qs = MicroXRFElementMap.objects.select_related(
            "measurement__sample__project"
        )
        return _project_qs(
            self.request.user, qs, "measurement__sample__project_id"
        )
