"""REST API ViewSets for geodata models."""

import json

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Landform
from .serializers import LandformGeoSerializer, LandformListSerializer

_BBOX_PARTS = 4
_MIN_SIMPLIFY_TOLERANCE = 0.001


class _LandformPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


def _parse_bbox(bbox_str: str) -> tuple[float, float, float, float] | None:
    """Parse a ``minx,miny,maxx,maxy`` string; return None on invalid input."""
    try:
        parts = [float(x) for x in bbox_str.split(",")]
        if len(parts) != _BBOX_PARTS:
            return None
        minx, miny, maxx, maxy = parts
        if minx >= maxx or miny >= maxy:
            return None
    except ValueError:
        return None
    else:
        return minx, miny, maxx, maxy


class LandformViewSet(ReadOnlyModelViewSet):
    """Read-only API for Murphy Landform region polygons.

    List endpoint (?bbox=minx,miny,maxx,maxy) returns GeoJSON using
    SpatiaLite AsGeoJSON() — no Python GEOS deserialization — and filters
    spatially so only polygons intersecting the viewport are returned.

    Without a bbox the list returns attributes only (no geometry) for fast
    browsing of all 56 k records.  Detail endpoint always returns full geometry.

    Morphogrid usage: GET /api/v1/landforms/?bbox=6.0,50.0,8.0,52.0
    """

    queryset = Landform.objects.all().defer("geometry")
    permission_classes = [IsAuthenticated]
    pagination_class = _LandformPagination
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

    def get_serializer_class(self) -> type:
        """Return GeoSerializer for detail, lightweight ListSerializer for list."""
        if self.action == "retrieve":
            return LandformGeoSerializer
        return LandformListSerializer

    def get_queryset(self) -> object:  # type: ignore[override]
        """Defer geometry for list actions; return full queryset for detail."""
        if self.action == "retrieve":
            return Landform.objects.all()
        return Landform.objects.all().defer("geometry")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="bbox",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Bounding box filter: `minx,miny,maxx,maxy` in WGS-84 (EPSG:4326). "
                    "When supplied the response is a GeoJSON FeatureCollection containing "
                    "only the landform polygons that intersect the viewport. "
                    "Geometry is serialised entirely in SpatiaLite (no Python GEOS "
                    "deserialisation) and simplified proportionally to the viewport width. "
                    "**Required for Morphogrid** — without bbox the list returns attributes "
                    "only (no geometry). Example: `?bbox=6.0,50.0,8.5,52.0`"
                ),
                examples=None,
            ),
        ],
        responses={200: LandformListSerializer(many=True)},
        summary="List landforms (add ?bbox=… to get GeoJSON with geometry)",
    )
    def list(  # type: ignore[override]
        self, request: Request, *args: object, **kwargs: object
    ) -> Response:
        """Return attributes-only list, or GeoJSON FeatureCollection when ?bbox= is given."""
        bbox_param = request.query_params.get("bbox", "")
        if not bbox_param:
            return super().list(request, *args, **kwargs)

        bbox = _parse_bbox(bbox_param)
        if bbox is None:
            return Response(
                {
                    "detail": "bbox must be minx,miny,maxx,maxy with minx<maxx and miny<maxy."
                },
                status=400,
            )

        from django.http import JsonResponse

        return JsonResponse(self._geojson_for_bbox(bbox), safe=False)  # type: ignore[return-value]

    def _geojson_for_bbox(
        self, bbox: tuple[float, float, float, float]
    ) -> dict:
        """Build a GeoJSON FeatureCollection for landforms intersecting *bbox*."""
        from django.db import connection

        minx, miny, maxx, maxy = bbox
        span = maxx - minx
        tolerance = span / 512.0

        # SpatiaLite's R-Tree index (idx_*) is only used via explicit subquery —
        # geometry__intersects generates Intersects() which causes a full table scan.
        # The idx subquery handles the bbox pre-filter; Intersects() refines it.
        _select = """
            SELECT
                l.id, l.murphy_code, l.name_str,
                l.division, l.province, l.continent,
        """
        _from = """
            FROM geodata_landform l
            WHERE l.geometry IS NOT NULL
              AND l.rowid IN (
                  SELECT pkid FROM idx_geodata_landform_geometry
                  WHERE xmin <= %s AND xmax >= %s AND ymin <= %s AND ymax >= %s
              )
              AND Intersects(l.geometry, BuildMbr(%s, %s, %s, %s))
        """
        bbox_params = [maxx, minx, maxy, miny, minx, miny, maxx, maxy]
        if tolerance >= _MIN_SIMPLIFY_TOLERANCE:
            sql = (
                _select
                + "COALESCE(AsGeoJSON(Simplify(l.geometry, %s)), AsGeoJSON(l.geometry))"
                + _from
            )
            params = [tolerance, *bbox_params]
        else:
            sql = _select + "AsGeoJSON(l.geometry)" + _from
            params = bbox_params

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        features = []
        for (
            pk,
            murphy_code,
            name_str,
            division,
            province,
            continent,
            geom_json,
        ) in rows:
            if not geom_json:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(geom_json),
                    "properties": {
                        "id": pk,
                        "murphy_code": murphy_code,
                        "name_str": name_str,
                        "division": division,
                        "province": province,
                        "continent": continent,
                    },
                }
            )

        return {"type": "FeatureCollection", "features": features}
