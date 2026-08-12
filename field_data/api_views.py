"""REST API ViewSets for field_data models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_gis.pagination import GeoJsonPagination

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import QuerySet
    from rest_framework.request import Request
    from rest_framework.serializers import BaseSerializer

    from prototype.models import Project

from analysis.selectors import LOCATION_MEASUREMENT_COUNTS
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
    LocationGeoSerializer,
    LocationMapSerializer,
    LocationWriteSerializer,
    SampleSerializer,
    SampleTypeSerializer,
    StudyAreaGeoSerializer,
    StudyAreaMapSerializer,
    StudyAreaWriteSerializer,
    TransectMapSerializer,
    TransectSerializer,
    TransectWriteSerializer,
)


def _project_qs(
    user: AbstractBaseUser | AnonymousUser, qs: QuerySet
) -> QuerySet:
    """Filter a queryset by accessible projects for the given user."""
    if user.is_superuser:
        return qs
    project_ids = _accessible_projects(user).values_list("id", flat=True)
    return qs.filter(project_id__in=project_ids)


_MAX_MAP_FEATURES = 5000


def _capped_list(qs: QuerySet, *, limit: int | None = None) -> list:
    """Evaluate *qs* into a list, guarding against an unbounded response.

    The map-dashboard `.map()` actions intentionally return everything at
    once (a map wants every marker in view, not a page at a time) rather
    than being paginated like the standard list endpoints — but with no
    upper bound at all, a project with enough records returns one
    arbitrarily large response. Raise instead of silently truncating:
    silently dropping markers would misrepresent the data on a scientific
    dashboard, and the map UI already has project/campaign/type filters to
    narrow scope instead. One extra row is fetched (limit + 1) so this is a
    single LIMIT query, not a separate COUNT.

    *limit* defaults to the module-level _MAX_MAP_FEATURES, read at call
    time (not as a default-argument value) so tests can patch it.
    """
    if limit is None:
        limit = _MAX_MAP_FEATURES
    capped = list(qs[: limit + 1])
    if len(capped) > limit:
        msg = (
            f"This request would return more than {limit} features. "
            "Narrow the result with a project/campaign/type filter."
        )
        raise ValidationError(msg)
    return capped


def _location_count_subquery(qs: QuerySet, location_lookup: str) -> Subquery:
    """Build a correlated-subquery row count of *qs* per outer Location.

    *location_lookup* is the field path from *qs*'s model back to Location
    (e.g. "location" for Sample, "sample__location" for LuminescenceDating/
    GrainSize) — always a chain of forward ForeignKeys, so it can't itself
    fan out (each row has exactly one sample, each sample exactly one
    location), unlike the reverse-relation joins this replaces.

    Used instead of a joined Count(..., distinct=True) annotation: combining
    multiple Count()s over different relations (sample, sample__x, sample__y)
    in one annotate() call makes Django join all of them simultaneously,
    fanning out to len(samples) * len(x) * len(y) intermediate rows per
    location before GROUP BY collapses them back down. A Subquery/OuterRef
    per count runs as an independent correlated subquery instead — no fan-out.
    """
    return Subquery(
        qs.filter(**{location_lookup: OuterRef("pk")})
        .order_by()
        .values(location_lookup)
        .annotate(c=Count("id"))
        .values("c"),
        output_field=IntegerField(),
    )


def _assert_can_add(
    user: AbstractBaseUser | AnonymousUser, project: Project
) -> None:
    """Raise PermissionDenied unless the user may add data to the project.

    Takes the Project instance (not a pk) so this can do a direct
    has_perm() object check — same shape as _assert_can_change below —
    instead of building the user's whole addable-projects queryset via
    guardian's get_objects_for_user() just to test membership of one pk.
    Mirrors raster_data/api_views.py's helper of the same name/shape — the
    duplication matches the existing pattern (_project_qs is also
    independently duplicated between field_data and raster_data) rather
    than a cross-app refactor for this phase.
    """
    if getattr(user, "is_superuser", False):
        return
    if not user.has_perm("prototype.add_project", project):
        msg = "You do not have permission to add data to this project."
        raise PermissionDenied(msg)


def _assert_can_change(
    user: AbstractBaseUser | AnonymousUser, project: Project | None
) -> None:
    """Raise PermissionDenied unless the user may change data in the project.

    Same has_perm("prototype.change_project", ...) check already used
    throughout the admin layer (prototype/mixins.py's
    ProjectBasedPermissionMixin etc.) via guardian's ObjectPermissionBackend
    — this is its first use from a DRF view.
    """
    if getattr(user, "is_superuser", False):
        return
    if project is None or not user.has_perm(
        "prototype.change_project", project
    ):
        msg = "You do not have permission to change data in this project."
        raise PermissionDenied(msg)


class LocationViewSet(UpdateModelMixin, ReadOnlyModelViewSet):
    """Paginated, filterable list of accessible locations.

    Update-only (no create): drawing a bare point with no other context is
    a poor UX fit versus the existing admin create form — the map
    dashboard's edit mode only ever reshapes/relocates an existing marker.

    permission_classes is IsAuthenticated rather than IsProjectMember:
    get_queryset() already scopes list/retrieve/map to accessible projects
    (the real read gate), and IsProjectMember's has_object_permission only
    checks view_project — wrong for a write path. perform_update() below
    does the real write-permission check (change_project).
    """

    permission_classes = [IsAuthenticated]
    # GeoJsonPagination wraps the page in a proper FeatureCollection shape
    # instead of DRF's generic {"results": [...]} — required since the
    # default read serializer (LocationGeoSerializer) is GeoJSON.
    pagination_class = GeoJsonPagination
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
        """Return the write serializer for updates; GeoJSON for reads.

        Architecture-review fix: this used to branch on
        `request.accepted_renderer.format` to pick between a flat
        lon/lat serializer and this GeoJSON one — but with no custom
        renderer registered, every real `application/json` client always
        got the flat shape, and GeoJSON was only reachable via the HTML
        browsable API. Standardized on GeoJSON always, matching
        StudyAreaViewSet's convention — this is GIS data, and a client
        wanting flat lon/lat can read `location.coordinates` itself.
        """
        if self.action in ("update", "partial_update"):
            return LocationWriteSerializer
        return LocationGeoSerializer

    def perform_update(self, serializer: BaseSerializer) -> None:
        """Reject the write unless the user may change data in this location's project.

        Literature data (data_source="literature") is never editable via the
        API, mirroring ProjectBasedPermissionMixin's identical rule for the
        admin (prototype/mixins.py) — it has no single owning project a
        change_project check could even target.
        """
        instance = cast("Location", serializer.instance)
        user = self.request.user
        if (
            not getattr(user, "is_superuser", False)
            and instance.data_source == "literature"
        ):
            msg = "Literature data cannot be edited."
            raise PermissionDenied(msg)
        _assert_can_change(user, instance.project)
        serializer.save()

    @action(detail=False, methods=["get"], url_path="map")
    def map(self, request: Request) -> Response:
        """Return a GeoJSON FeatureCollection for the map dashboard's locations overlay."""
        qs = (
            self.get_queryset()
            .exclude(location__isnull=True)
            .annotate(
                sample_count=Coalesce(
                    _location_count_subquery(Sample.objects.all(), "location"),
                    0,
                ),
                **{
                    name: Coalesce(
                        _location_count_subquery(model.objects.all(), lookup),
                        0,
                    )
                    for name, (
                        model,
                        lookup,
                    ) in LOCATION_MEASUREMENT_COUNTS.items()
                },
            )
        )
        serializer = LocationMapSerializer(
            _capped_list(qs), many=True, context={"request": request}
        )
        return Response(serializer.data)


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


class StudyAreaViewSet(
    CreateModelMixin, UpdateModelMixin, ReadOnlyModelViewSet
):
    """List of study areas scoped to accessible projects; create/update supported.

    permission_classes is IsAuthenticated rather than IsProjectMember — see
    LocationViewSet's docstring for why. perform_create()/perform_update()
    below do the real write-permission checks (add_project/change_project).
    """

    serializer_class = StudyAreaGeoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = GeoJsonPagination
    filterset_fields = ["project"]
    search_fields = ["label"]
    ordering_fields = ["label"]
    ordering = ["label"]

    def get_queryset(self) -> QuerySet[StudyArea]:
        """Return study areas for projects the user can access."""
        return _project_qs(
            self.request.user, StudyArea.objects.select_related("project")
        )

    def get_serializer_class(self) -> type[BaseSerializer]:
        """Return the write serializer for create/update; GeoJSON otherwise."""
        if self.action in ("create", "update", "partial_update"):
            return StudyAreaWriteSerializer
        return StudyAreaGeoSerializer

    def perform_create(self, serializer: BaseSerializer) -> None:
        """Reject the write unless the user may add data to the target project."""
        validated_data = cast("dict[str, Any]", serializer.validated_data)
        project = validated_data["project"]
        _assert_can_add(self.request.user, project)
        serializer.save()

    def perform_update(self, serializer: BaseSerializer) -> None:
        """Reject the write unless permitted for both the object and its target project.

        'project' is a writable field — without this second check, a user
        with change_project on the study area's current project could PATCH
        it into any other project in the system, bypassing that project's
        own add permission entirely.
        """
        instance = cast("StudyArea", serializer.instance)
        _assert_can_change(self.request.user, instance.project)
        validated_data = cast("dict[str, Any]", serializer.validated_data)
        new_project = validated_data.get("project", instance.project)
        if new_project.pk != instance.project.pk:
            _assert_can_add(self.request.user, new_project)
        serializer.save()

    @action(detail=False, methods=["get"], url_path="map")
    def map(self, request: Request) -> Response:
        """Return a GeoJSON FeatureCollection for the map dashboard's study areas overlay."""
        qs = self.get_queryset().exclude(geometry__isnull=True)
        serializer = StudyAreaMapSerializer(
            _capped_list(qs), many=True, context={"request": request}
        )
        return Response(serializer.data)


class TransectViewSet(
    CreateModelMixin, UpdateModelMixin, ReadOnlyModelViewSet
):
    """List of transects scoped to accessible projects; create/update supported.

    permission_classes is IsAuthenticated rather than IsProjectMember — see
    LocationViewSet's docstring for why.
    """

    serializer_class = TransectSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["study_area", "campaign"]
    search_fields = ["identifier"]
    ordering_fields = ["identifier"]
    ordering = ["identifier"]

    def get_queryset(self) -> QuerySet[Transect]:
        """Return transects for study areas the user can access."""
        user = self.request.user
        qs = Transect.objects.select_related("study_area__project", "campaign")
        if user.is_superuser:
            return qs
        project_ids = _accessible_projects(user).values_list("id", flat=True)
        return qs.filter(study_area__project_id__in=project_ids)

    def get_serializer_class(self) -> type[BaseSerializer]:
        """Return the write serializer for create/update; the default otherwise."""
        if self.action in ("create", "update", "partial_update"):
            return TransectWriteSerializer
        return TransectSerializer

    def perform_create(self, serializer: BaseSerializer) -> None:
        """Reject the write unless the user may add data to the transect's study area's project."""
        validated_data = cast("dict[str, Any]", serializer.validated_data)
        study_area = validated_data["study_area"]
        _assert_can_add(self.request.user, study_area.project)
        serializer.save()

    def perform_update(self, serializer: BaseSerializer) -> None:
        """Reject the write unless permitted for both the object and its target project.

        See StudyAreaViewSet.perform_update for why.
        """
        instance = cast("Transect", serializer.instance)
        _assert_can_change(self.request.user, instance.study_area.project)
        validated_data = cast("dict[str, Any]", serializer.validated_data)
        new_study_area = validated_data.get("study_area", instance.study_area)
        if new_study_area.project.pk != instance.study_area.project.pk:
            _assert_can_add(self.request.user, new_study_area.project)
        serializer.save()

    @action(detail=False, methods=["get"], url_path="map")
    def map(self, request: Request) -> Response:
        """Return a GeoJSON FeatureCollection for the map dashboard's transects overlay."""
        qs = self.get_queryset().exclude(multiline__isnull=True)
        serializer = TransectMapSerializer(
            _capped_list(qs), many=True, context={"request": request}
        )
        return Response(serializer.data)


class LayerViewSet(ReadOnlyModelViewSet):
    """Read-only list of stratigraphic layers scoped to accessible projects."""

    serializer_class = LayerSerializer
    permission_classes = [IsProjectMember]
    filterset_fields = ["location"]
    ordering_fields = ["location", "depth_top"]
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
    ordering_fields = ["name_en"]
    ordering = ["name_en"]


class SampleTypeViewSet(ReadOnlyModelViewSet):
    """Lookup table — no project scoping needed."""

    queryset = SampleType.objects.all()
    serializer_class = SampleTypeSerializer
    ordering_fields = ["word"]
    ordering = ["word"]
