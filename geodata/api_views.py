"""REST API ViewSets for geodata models."""

import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.contrib.gis.geos import Polygon
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_GET
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
_MVT_EXTENT = 4096
_MVT_BUFFER = 64
_SRID_WGS84 = 4326  # matches Landform.geometry's fixed srid=4326


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

    List endpoint (?bbox=minx,miny,maxx,maxy) returns GeoJSON using the
    portable GeoDjango ORM (AsGeoJSON() + the __intersects lookup) — no
    Python GEOS deserialization — and filters spatially so only polygons
    intersecting the viewport are returned. Works identically on PostGIS
    (production) and SpatiaLite (dev/test).

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
                    "Geometry is serialised via the database's AsGeoJSON() (no Python GEOS "
                    "deserialisation); geometry is not simplified. "
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
        """Build a GeoJSON FeatureCollection for landforms intersecting *bbox*.

        Uses the GeoDjango ORM (not raw SQL) so this works identically on
        PostGIS and SpatiaLite: __bboverlaps uses the spatial index for a
        cheap bbox pre-filter, __intersects refines it, and AsGeoJSON()
        serialises geometry inside the database (no Python GEOS
        deserialisation of the full geometry).
        """
        bbox_poly = Polygon.from_bbox(bbox)
        bbox_poly.srid = 4326
        rows = (
            Landform.objects.filter(
                geometry__isnull=False,
                geometry__bboverlaps=bbox_poly,
                geometry__intersects=bbox_poly,
            )
            .annotate(geojson=AsGeoJSON("geometry"))
            .values(
                "id",
                "murphy_code",
                "name_str",
                "division",
                "province",
                "continent",
                "geojson",
            )
        )

        features = []
        for row in rows:
            geom_json = row["geojson"]
            if not geom_json:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(geom_json),
                    "properties": {
                        "id": row["id"],
                        "murphy_code": row["murphy_code"],
                        "name_str": row["name_str"],
                        "division": row["division"],
                        "province": row["province"],
                        "continent": row["continent"],
                    },
                }
            )

        return {"type": "FeatureCollection", "features": features}


@login_required
@require_GET
def landform_tile(
    request: HttpRequest,  # noqa: ARG001 — required by Django's URL dispatch signature
    z: int,
    x: int,
    y: int,
) -> HttpResponse:
    """Serve a Mapbox Vector Tile (MVT) of landform polygons for tile {z}/{x}/{y}.

    PostGIS-only: ST_AsMVT/ST_AsMVTGeom have no SpatiaLite equivalent, so this
    returns 501 on other backends rather than letting the raw SQL fail with a
    vendor-specific error — deliberate and visible, given the bug this
    project already shipped once from vendor-specific SQL going untested on
    SpatiaLite (see LandformViewSet's bbox endpoint history).

    This is additive: the existing GeoJSON `?bbox=` endpoint on
    ``LandformViewSet`` (required by Morphogrid) is untouched. Locations,
    StudyAreas, and Transects deliberately stay on GeoJSON — they're orders
    of magnitude smaller than the 56k landform rows, and editing (a planned
    future feature) needs individually addressable vector features, which
    vector tiles don't provide.

    The WHERE clause tests against the tile envelope transformed into
    `geometry`'s own native SRID (4326), not the other way around: geometry
    is only ST_Transform'd to 3857 for the small, already-filtered result
    set inside ST_AsMVTGeom. Transforming `geometry` itself inside WHERE (as
    an earlier version of this query did) makes the expression unindexable,
    forcing PostGIS to transform and test all ~56k rows on every request —
    transforming the one tile envelope instead lets `geometry`'s GiST index
    do the filtering.
    """
    if connection.vendor != "postgresql":
        return HttpResponse(status=501)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH tile_bounds AS (
                SELECT ST_TileEnvelope(%s, %s, %s) AS geom_3857
            ),
            tile_bounds_native AS (
                SELECT ST_Transform(geom_3857, %s) AS geom FROM tile_bounds
            )
            SELECT ST_AsMVT(tile, 'landforms', %s, 'geom') FROM (
                SELECT id, murphy_code, name_str, division, province, continent,
                       ST_AsMVTGeom(
                           ST_Transform(geometry, 3857),
                           (SELECT geom_3857 FROM tile_bounds),
                           %s, %s, true
                       ) AS geom
                FROM geodata_landform, tile_bounds_native
                WHERE geometry IS NOT NULL
                  AND geometry && tile_bounds_native.geom
                  AND ST_Intersects(geometry, tile_bounds_native.geom)
            ) AS tile
            """,
            [z, x, y, _SRID_WGS84, _MVT_EXTENT, _MVT_EXTENT, _MVT_BUFFER],
        )
        row = cursor.fetchone()

    tile_data = bytes(row[0]) if row and row[0] is not None else b""
    response = HttpResponse(tile_data, content_type="application/x-protobuf")
    # Tiles only change when import_landforms reruns (an infrequent bulk
    # operation) — safe to cache for a day and meaningfully cuts PostGIS load.
    response["Cache-Control"] = "public, max-age=86400"
    return response
