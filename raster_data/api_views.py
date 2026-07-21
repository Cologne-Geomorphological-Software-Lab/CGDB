"""REST API ViewSets for raster_data models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.db.models import Model
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import QuerySet
    from rest_framework.request import Request
    from rest_framework.serializers import BaseSerializer

from prototype.mixins import _accessible_projects, _addable_projects

from .models import DataSource, RasterDataset, RasterScene
from .serializers import (
    DataSourceSerializer,
    RasterDatasetSerializer,
    RasterDatasetWriteSerializer,
    RasterSceneSerializer,
    RasterSceneWriteSerializer,
    _ManifestSceneSerializer,
)


def _project_qs[T: Model](
    user: AbstractBaseUser | AnonymousUser, qs: QuerySet[T]
) -> QuerySet[T]:
    """Filter a queryset by accessible projects for the given user."""
    if getattr(user, "is_superuser", False):
        return qs
    project_ids = _accessible_projects(user).values_list("id", flat=True)
    return qs.filter(project_id__in=project_ids)


def _assert_can_add(
    user: AbstractBaseUser | AnonymousUser, project_id: int
) -> None:
    """Raise PermissionDenied unless the user may add data to the project."""
    if getattr(user, "is_superuser", False):
        return
    if not _addable_projects(user).filter(pk=project_id).exists():
        msg = "You do not have permission to add data to this project."
        raise PermissionDenied(msg)


class DataSourceViewSet(ReadOnlyModelViewSet):
    """Read-only API for data source / sensor / product descriptions."""

    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["provider", "product_type"]
    search_fields = ["name", "provider", "platform", "product_type"]
    ordering_fields = ["name", "provider"]
    ordering = ["name"]


class RasterSceneViewSet(CreateModelMixin, ReadOnlyModelViewSet):
    """API for georeferenced raster scenes (read + create)."""

    permission_classes = [IsAuthenticated]
    filterset_fields = ["project", "data_source", "crs"]
    search_fields = ["corpus_path", "crs"]
    ordering_fields = ["acquisition_date", "data_source__name"]
    ordering = ["-acquisition_date"]

    def get_queryset(self) -> QuerySet[RasterScene]:
        """Return raster scenes for projects the user can access."""
        return _project_qs(
            self.request.user,
            RasterScene.objects.select_related("data_source", "project"),
        )

    def get_serializer_class(self) -> type[BaseSerializer]:
        """Return the write serializer for create, the read serializer otherwise."""
        if self.action == "create":
            return RasterSceneWriteSerializer
        return RasterSceneSerializer

    def perform_create(self, serializer: BaseSerializer) -> None:
        """Save the scene after checking the user may add to its project."""
        validated_data = cast("dict[str, Any]", serializer.validated_data)
        project_id = validated_data["project"].pk
        _assert_can_add(self.request.user, project_id)
        serializer.save()


class RasterDatasetViewSet(CreateModelMixin, ReadOnlyModelViewSet):
    """API for named raster datasets (read + create), with a manifest action."""

    permission_classes = [IsAuthenticated]
    filterset_fields = ["project"]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["name", "modified_at"]
    ordering = ["-modified_at"]

    def get_queryset(self) -> QuerySet[RasterDataset]:
        """Return raster datasets for projects the user can access."""
        return _project_qs(
            self.request.user,
            RasterDataset.objects.select_related("project"),
        )

    def get_serializer_class(self) -> type[BaseSerializer]:
        """Return the write serializer for create, the read serializer otherwise."""
        if self.action == "create":
            return RasterDatasetWriteSerializer
        return RasterDatasetSerializer

    def perform_create(self, serializer: BaseSerializer) -> None:
        """Save the dataset after checking the user may add to its project."""
        validated_data = cast("dict[str, Any]", serializer.validated_data)
        project_id = validated_data["project"].pk
        _assert_can_add(self.request.user, project_id)
        serializer.save()

    @action(detail=True, methods=["get"], url_path="manifest")
    def manifest(
        self,
        _request: Request,
        pk: int | None = None,  # noqa: ARG002 -- name required by DRF URL routing
    ) -> Response:
        """Return a JSON manifest of all scenes in this dataset.

        Includes paths and factual metadata of each scene.
        Classification rasters (n_classes set) are identified at query time
        via spatial intersection — not as a separate list.
        """
        dataset = self.get_object()
        scenes = dataset.scenes.select_related("data_source").order_by(
            "acquisition_date"
        )
        return Response(
            {
                "id": dataset.pk,
                "name": dataset.name,
                "slug": dataset.slug,
                "description": dataset.description,
                "scenes": _ManifestSceneSerializer(scenes, many=True).data,
            }
        )
