"""Views for the prototype app: documentation, dashboard, map, and GeoJSON endpoints."""

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import Count, Q, QuerySet
from django.db.models.functions import TruncMonth
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import make_aware, now
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from analysis.models import (
    GenericMeasurement,
    GrainSize,
    LuminescenceDating,
    RadiocarbonDating,
)
from field_data.models import Location, Sample, StudyArea, Transect
from prototype.mixins import _accessible_projects
from prototype.models import Project

logger = logging.getLogger(__name__)


def documentation(request: HttpRequest, filepath: str) -> HttpResponse:
    """Serve a static documentation file, or 404 if it does not exist."""
    doc_path = Path(settings.BASE_DIR) / "static" / "docs" / filepath
    if not doc_path.exists():
        return render(request, "404.html", status=404)
    return render(
        request,
        "documentation.html",
        {"filepath": f"/static/docs/{filepath}"},
    )


def logout_view(request: HttpRequest) -> HttpResponse:
    """Log out the current user and redirect to the site root."""
    logout(request)
    return redirect("/")


_PERIOD_OPTIONS = [
    {"days": 30, "label": "30 days"},
    {"days": 90, "label": "90 days"},
    {"days": 365, "label": "1 year"},
]

_LOCATION_TYPE_LABELS = {
    "sampling_location": "Sampling Location",
    "camp": "Camp",
    "road_access": "Road Access",
    "infrastructure": "Infrastructure",
    "weather_station": "Weather Station",
    "survey_point": "Survey Point",
    "observation": "Observation",
    "other": "Other",
}


_DASHBOARD_NAV = [
    {"title": _("Overview"), "link": "/", "active_path": "/"},
    {"title": _("Map"), "link": "/map/", "active_path": "/map/"},
]


def _nav(request: HttpRequest | None) -> list:
    path = request.path if request else ""
    return [
        {
            "title": n["title"],
            "link": n["link"],
            "active": path == n["active_path"],
        }
        for n in _DASHBOARD_NAV
    ]


def map_dashboard(request: HttpRequest) -> HttpResponse:
    """Render the full-screen map dashboard page."""
    from django.contrib import admin as _admin

    context = _admin.site.each_context(request)
    context["navigation"] = _nav(request)
    context["geojson_urls"] = {
        "locations": reverse("locations_geojson"),
        "study_areas": reverse("study_areas_geojson"),
        "transects": reverse("transects_geojson"),
        "landforms": reverse("landforms_geojson"),
    }
    return render(request, "admin/map_dashboard.html", context)


@require_GET
def locations_geojson(request: HttpRequest) -> HttpResponse:
    """Return a GeoJSON FeatureCollection of all accessible locations."""
    user = cast("Any", request.user)
    if user.is_superuser:
        qs = Location.objects.exclude(location__isnull=True)
    else:
        project_ids = _accessible_projects(request.user).values_list(
            "id",
            flat=True,
        )
        qs = Location.objects.filter(
            Q(project_id__in=project_ids) | Q(data_source="literature"),
        ).exclude(
            location__isnull=True,
        )

    qs = qs.select_related("project", "campaign", "exposure_type").annotate(
        sample_count=Count("sample", distinct=True),
        luminescence_count=Count(
            "sample__luminescence_datings", distinct=True
        ),
        grain_size_count=Count("sample__grain_sizes", distinct=True),
    )

    features = []
    for loc in qs:
        # loc.location is excluded from being NULL above; annotate()d fields
        # (sample_count, ...) and get_location_type_display() are added
        # dynamically by Django and are invisible to static analysis.
        loc_dynamic = cast("Any", loc)
        point = loc_dynamic.location
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [point.x, point.y],
                },
                "properties": {
                    "id": loc.pk,
                    "identifier": loc.identifier,
                    "project": str(loc.project) if loc.project else None,
                    "data_source": loc.data_source,
                    "location_type": loc.location_type,
                    "location_type_display": loc_dynamic.get_location_type_display(),
                    "campaign": loc.campaign.label if loc.campaign else None,
                    "date_of_record": loc.date_of_record.isoformat()
                    if loc.date_of_record
                    else None,
                    "altitude": loc.altitude,
                    "exposure_type": loc.exposure_type.name_en
                    if loc.exposure_type
                    else None,
                    "sample_count": loc_dynamic.sample_count,
                    "luminescence_count": loc_dynamic.luminescence_count,
                    "grain_size_count": loc_dynamic.grain_size_count,
                    "admin_url": reverse(
                        "admin:field_data_location_change", args=[loc.pk]
                    ),
                },
            }
        )
    return JsonResponse({"type": "FeatureCollection", "features": features})


@require_GET
def study_areas_geojson(request: HttpRequest) -> HttpResponse:
    """Return a GeoJSON FeatureCollection of all accessible study areas."""
    user = cast("Any", request.user)
    if user.is_superuser:
        qs = StudyArea.objects.exclude(geometry__isnull=True)
    else:
        project_ids = _accessible_projects(request.user).values_list(
            "id", flat=True
        )
        qs = StudyArea.objects.filter(project_id__in=project_ids).exclude(
            geometry__isnull=True
        )

    features = []
    for sa in qs.select_related("project"):
        # get_*_display() is added dynamically by Django for choices fields
        # and is invisible to static analysis.
        sa_dynamic = cast("Any", sa)
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(sa.geometry.geojson),
                "properties": {
                    "id": sa.pk,
                    "label": sa.label,
                    "project": str(sa.project),
                    "climate_koeppen": sa.climate_koeppen,
                    "climate_koeppen_display": sa_dynamic.get_climate_koeppen_display(),
                    "ecozone_schultz": sa.ecozone_schultz,
                    "ecozone_schultz_display": sa_dynamic.get_ecozone_schultz_display(),
                    "admin_url": reverse(
                        "admin:field_data_studyarea_change", args=[sa.pk]
                    ),
                },
            }
        )
    return JsonResponse({"type": "FeatureCollection", "features": features})


@require_GET
def transects_geojson(request: HttpRequest) -> HttpResponse:
    """Return a GeoJSON FeatureCollection of all accessible transects."""
    user = cast("Any", request.user)
    if user.is_superuser:
        qs = Transect.objects.exclude(multiline__isnull=True)
    else:
        project_ids = _accessible_projects(request.user).values_list(
            "id", flat=True
        )
        qs = Transect.objects.filter(
            study_area__project_id__in=project_ids
        ).exclude(multiline__isnull=True)

    features = [
        {
            "type": "Feature",
            "geometry": json.loads(t.multiline.geojson),
            "properties": {
                "id": t.pk,
                "identifier": t.identifier,
                "study_area": str(t.study_area),
                "campaign": t.campaign.label if t.campaign else None,
                "admin_url": reverse(
                    "admin:field_data_transect_change", args=[t.pk]
                ),
            },
        }
        for t in qs.select_related("study_area", "campaign")
    ]
    return JsonResponse({"type": "FeatureCollection", "features": features})


_LANDFORM_SIMPLIFY_THRESHOLD = (
    1e-4  # degrees (~11 m); below this no simplification
)


def _parse_bbox(bbox_param: str) -> tuple[float, float, float, float] | None:
    """Parse and clamp a 'minx,miny,maxx,maxy' string; return None on failure."""
    try:
        minx, miny, maxx, maxy = (float(v) for v in bbox_param.split(","))
    except (ValueError, TypeError):
        return None
    minx = max(minx, -180.0)
    maxx = min(maxx, 180.0)
    miny = max(miny, -90.0)
    maxy = min(maxy, 90.0)
    if maxx <= minx or maxy <= miny:
        return None
    return minx, miny, maxx, maxy


@require_GET
def landforms_geojson(request: HttpRequest) -> HttpResponse:
    """Return a viewport-filtered GeoJSON FeatureCollection of landform polygons.

    Geometry is serialised entirely in SpatiaLite via AsGeoJSON() so Python
    never deserialises GEOS objects.  At low zoom Simplify() reduces vertex
    count proportionally to the viewport width.
    """
    from django.contrib.gis.geos import Polygon
    from django.db.models.expressions import RawSQL

    from geodata.models import Landform

    bbox_param = request.GET.get("bbox", "")
    bbox = _parse_bbox(bbox_param) if bbox_param else None
    if bbox is None:
        return JsonResponse({"type": "FeatureCollection", "features": []})

    span = bbox[2] - bbox[0]
    tolerance = span / 512.0

    bbox_poly = Polygon.from_bbox(bbox)
    bbox_poly.srid = 4326
    qs = Landform.objects.exclude(geometry__isnull=True).filter(
        geometry__intersects=bbox_poly,
    )

    if tolerance >= _LANDFORM_SIMPLIFY_THRESHOLD:
        # SpatiaLite uses AsGeoJSON / Simplify (without ST_ prefix).
        # COALESCE falls back to full geometry when Simplify returns NULL
        # (degenerate polygon collapses to a line at the given tolerance).
        geom_sql = RawSQL(
            "COALESCE(AsGeoJSON(Simplify(geometry, %s)), AsGeoJSON(geometry))",
            [tolerance],
        )
    else:
        geom_sql = RawSQL("AsGeoJSON(geometry)", [])

    rows = qs.values_list(
        "id",
        "murphy_code",
        "name_str",
        "division",
        "province",
        "continent",
        geom_sql,
    )

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
    return JsonResponse({"type": "FeatureCollection", "features": features})


_WMS_WHITELIST = ["services.bgr.de"]


@require_GET
def wms_proxy(request: HttpRequest) -> HttpResponse:
    """Server-side proxy for WMS GetFeatureInfo to avoid browser CORS restrictions."""
    url = request.GET.get("url", "")
    host = urlparse(url).hostname or ""
    if not any(host == w or host.endswith("." + w) for w in _WMS_WHITELIST):
        return HttpResponse("Forbidden", status=403)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310  # nosec B310 — hostname validated against _WMS_WHITELIST above
            content = resp.read()
            ct = resp.headers.get("Content-Type", "text/xml")
    except (urllib.error.URLError, OSError):
        return HttpResponse("", status=502)
    return HttpResponse(content, content_type=ct)


def dashboard_callback(request: HttpRequest | None, context: dict) -> dict:
    """Populate the Unfold dashboard context with stats and navigation."""
    try:
        period_days = int(request.GET.get("period", 30)) if request else 30
    except (ValueError, TypeError):
        period_days = 30
    if period_days not in {p["days"] for p in _PERIOD_OPTIONS}:
        period_days = 30

    context.update(stat_data(period_days))
    context["navigation"] = _nav(request)
    context["filters"] = [
        {
            "title": _(p["label"]),
            "link": f"?period={p['days']}",
            "active": period_days == p["days"],
        }
        for p in _PERIOD_OPTIONS
    ]
    return context


def stat_data(period_days: int = 30) -> dict:
    """Compute dashboard statistics for the given time window in days."""
    now = timezone.now()
    since = now - timedelta(days=period_days)
    logger.debug("stat_data called at %s (period=%d days)", now, period_days)

    def _pct(count: int, total: int) -> float:
        return round(count / total * 100, 2) if total > 0 else 0

    def _footer(count: int, total: int) -> str:
        if count == 0:
            return mark_safe(  # nosec B308 — pure static literal, no user input
                '<span class="text-gray-500 dark:text-gray-400">No new entries</span>'
            )
        pct = _pct(count, total)
        color = (
            "text-green-700 dark:text-green-400"
            if pct > 0
            else "text-red-600 dark:text-red-400"
        )
        sign = "+" if pct > 0 else ""
        return format_html(
            '<strong class="{} font-semibold">{}{}</strong>&nbsp; last {} days',
            color,
            sign,
            intcomma(pct),
            period_days,
        )

    def _total_and_period(queryset: QuerySet) -> tuple[int, int]:
        """Return (total count, count in [since, now)) in a single query."""
        result = queryset.aggregate(
            total=Count("id"),
            period=Count(
                "id", filter=Q(created_at__gte=since, created_at__lt=now)
            ),
        )
        return result["total"], result["period"]

    # Projects
    project_total, project_period_count = _total_and_period(
        Project.objects.all()
    )
    logger.debug("Project total: %s", project_total)

    # Locations
    location_total, location_period_count = _total_and_period(
        Location.objects.all()
    )

    # Samples
    sample_total, sample_period_count = _total_and_period(Sample.objects.all())

    # Measurements
    measurement_models = [
        GenericMeasurement,
        GrainSize,
        LuminescenceDating,
        RadiocarbonDating,
    ]
    measurement_totals = [
        _total_and_period(m.objects.all()) for m in measurement_models
    ]
    measurements_total = sum(total for total, _period in measurement_totals)
    measurements_period_count = sum(
        period for _total, period in measurement_totals
    )
    generic_total, grain_size_total, luminescence_total, radiocarbon_total = (
        total for total, _period in measurement_totals
    )

    # Location type breakdown
    location_by_type_rows = list(
        Location.objects.values("location_type")
        .annotate(n=Count("id"))
        .order_by("-n")
    )
    location_max = max((row["n"] for row in location_by_type_rows), default=1)
    location_breakdown = [
        {
            "label": _LOCATION_TYPE_LABELS.get(
                row["location_type"],
                row["location_type"].replace("_", " ").title(),
            ),
            "n": row["n"],
            "pct": round(row["n"] / location_max * 100),
        }
        for row in location_by_type_rows
    ]
    literature_count = Location.objects.filter(
        data_source="literature"
    ).count()
    internal_count = Location.objects.filter(data_source="internal").count()

    return {
        "project": [
            {
                "title": "Projects",
                "metric": f"{project_total}",
                "footer": _footer(project_period_count, project_total),
            },
            {
                "title": "Locations",
                "metric": f"{location_total}",
                "footer": _footer(location_period_count, location_total),
            },
            {
                "title": "Samples",
                "metric": f"{sample_total}",
                "footer": _footer(sample_period_count, sample_total),
            },
            {
                "title": "Measurements",
                "metric": f"{measurements_total}",
                "footer": _footer(
                    measurements_period_count, measurements_total
                ),
            },
        ],
        "location_breakdown": location_breakdown,
        "literature_count": literature_count,
        "internal_count": internal_count,
        "performance": [
            {
                "title": _("Sedimentological Measurements"),
                "metric": f"{generic_total + grain_size_total}",
                "chart": json.dumps(
                    {
                        "datasets": [
                            {
                                "data": _build_monthly_performance(
                                    [GenericMeasurement, GrainSize],
                                ),
                                "borderColor": "var(--color-primary-700)",
                            },
                        ],
                    },
                ),
            },
            {
                "title": _("Geochronological Measurements"),
                "metric": f"{luminescence_total + radiocarbon_total}",
                "chart": json.dumps(
                    {
                        "datasets": [
                            {
                                "data": _build_monthly_performance(
                                    [LuminescenceDating, RadiocarbonDating],
                                ),
                                "borderColor": "var(--color-primary-300)",
                            },
                        ],
                    },
                ),
            },
            {
                "title": _("Field Samples Collected"),
                "metric": f"{sample_total}",
                "chart": json.dumps(
                    {
                        "datasets": [
                            {
                                "data": _build_monthly_performance([Sample]),
                                "borderColor": "var(--color-primary-500)",
                            },
                        ],
                    },
                ),
            },
        ],
    }


MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _build_monthly_performance(model_classes: list) -> list:
    """Return a list of [month_label, count] pairs for the last 12 months.

    Uses one TruncMonth-grouped query per model instead of one .count() per
    month, so N models cost N queries total instead of 12*N.
    """
    today = now()
    months = [
        (
            (today - relativedelta(months=i)).year,
            (today - relativedelta(months=i)).month,
        )
        for i in range(11, -1, -1)
    ]
    counts = dict.fromkeys(months, 0)
    range_start = make_aware(datetime(months[0][0], months[0][1], 1))

    for model in model_classes:
        rows = (
            model.objects.filter(created_at__gte=range_start)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(n=Count("id"))
        )
        for row in rows:
            key = (row["month"].year, row["month"].month)
            if key in counts:
                counts[key] += row["n"]

    return [
        [f"{MONTH_NAMES[month - 1]} {year}", counts[(year, month)]]
        for year, month in months
    ]
