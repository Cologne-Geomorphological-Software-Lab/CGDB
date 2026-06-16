"""Views for the prototype app: documentation, dashboard, map, and GeoJSON endpoints."""

import json
import logging
import urllib.error
import urllib.request
from calendar import monthrange
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
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
    return render(request, "admin/map_dashboard.html", context)


@require_GET
def locations_geojson(request: HttpRequest) -> HttpResponse:
    """Return a GeoJSON FeatureCollection of all accessible locations."""
    if request.user.is_superuser:
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

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [loc.location.x, loc.location.y],
            },
            "properties": {
                "id": loc.id,
                "identifier": loc.identifier,
                "project": str(loc.project) if loc.project else None,
                "data_source": loc.data_source,
                "location_type": loc.location_type,
                "location_type_display": loc.get_location_type_display(),
                "campaign": loc.campaign.label if loc.campaign else None,
                "date_of_record": loc.date_of_record.isoformat()
                if loc.date_of_record
                else None,
                "altitude": loc.altitude,
                "exposure_type": loc.exposure_type.name_en
                if loc.exposure_type
                else None,
                "sample_count": loc.sample_count,
                "luminescence_count": loc.luminescence_count,
                "grain_size_count": loc.grain_size_count,
                "admin_url": reverse(
                    "admin:field_data_location_change", args=[loc.id]
                ),
            },
        }
        for loc in qs
    ]
    return JsonResponse({"type": "FeatureCollection", "features": features})


@require_GET
def study_areas_geojson(request: HttpRequest) -> HttpResponse:
    """Return a GeoJSON FeatureCollection of all accessible study areas."""
    if request.user.is_superuser:
        qs = StudyArea.objects.exclude(geometry__isnull=True)
    else:
        project_ids = _accessible_projects(request.user).values_list(
            "id", flat=True
        )
        qs = StudyArea.objects.filter(project_id__in=project_ids).exclude(
            geometry__isnull=True
        )

    features = [
        {
            "type": "Feature",
            "geometry": json.loads(sa.geometry.geojson),
            "properties": {
                "id": sa.id,
                "label": sa.label,
                "project": str(sa.project),
                "climate_koeppen": sa.climate_koeppen,
                "climate_koeppen_display": sa.get_climate_koeppen_display(),
                "ecozone_schultz": sa.ecozone_schultz,
                "ecozone_schultz_display": sa.get_ecozone_schultz_display(),
                "admin_url": reverse(
                    "admin:field_data_studyarea_change", args=[sa.id]
                ),
            },
        }
        for sa in qs.select_related("project")
    ]
    return JsonResponse({"type": "FeatureCollection", "features": features})


@require_GET
def transects_geojson(request: HttpRequest) -> HttpResponse:
    """Return a GeoJSON FeatureCollection of all accessible transects."""
    if request.user.is_superuser:
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
                "id": t.id,
                "identifier": t.identifier,
                "study_area": str(t.study_area),
                "campaign": t.campaign.label if t.campaign else None,
                "admin_url": reverse(
                    "admin:field_data_transect_change", args=[t.id]
                ),
            },
        }
        for t in qs.select_related("study_area", "campaign")
    ]
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
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            content = resp.read()
            ct = resp.headers.get("Content-Type", "text/xml")
    except (urllib.error.URLError, OSError):
        return HttpResponse("", status=502)
    return HttpResponse(content, content_type=ct)


def dashboard_callback(request: HttpRequest | None, context: dict) -> dict:
    """Populate the Unfold dashboard context with stats and navigation."""
    try:
        period_days = int(request.GET.get("period", 30))
    except (ValueError, TypeError, AttributeError):
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

    def _footer(count: int, total: int) -> str:  # nosec B703, B308 — only floats interpolated
        if count == 0:
            return mark_safe(
                '<span class="text-gray-500 dark:text-gray-400">No new entries</span>'
            )
        pct = _pct(count, total)
        color = (
            "text-green-700 dark:text-green-400"
            if pct > 0
            else "text-red-600 dark:text-red-400"
        )
        sign = "+" if pct > 0 else ""
        return mark_safe(  # noqa: S308
            f'<strong class="{color} font-semibold">{sign}{intcomma(pct)}%</strong>'
            f"&nbsp; last {period_days} days",
        )

    # Projects
    project_total = Project.objects.count()
    project_period_count = Project.objects.filter(
        created_at__gte=since,
        created_at__lt=now,
    ).count()
    logger.debug("Project total: %s", project_total)

    # Locations
    location_total = Location.objects.count()
    location_period_count = Location.objects.filter(
        created_at__gte=since,
        created_at__lt=now,
    ).count()

    # Samples
    sample_total = Sample.objects.count()
    sample_period_count = Sample.objects.filter(
        created_at__gte=since,
        created_at__lt=now,
    ).count()

    # Measurements
    measurement_models = [
        GenericMeasurement,
        GrainSize,
        LuminescenceDating,
        RadiocarbonDating,
    ]
    measurements_total = sum(m.objects.count() for m in measurement_models)
    measurements_period_count = sum(
        m.objects.filter(created_at__gte=since, created_at__lt=now).count()
        for m in measurement_models
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
                "metric": f"{GenericMeasurement.objects.count() + GrainSize.objects.count()}",
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
                "metric": f"{LuminescenceDating.objects.count() + RadiocarbonDating.objects.count()}",
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
    """Return a list of [month_label, count] pairs for the last 12 months."""
    today = now()
    result = []
    for i in range(11, -1, -1):
        month_date = today - relativedelta(months=i)
        year = month_date.year
        month = month_date.month
        start_date = make_aware(datetime(year, month, 1))
        end_date = make_aware(
            datetime(year, month, monthrange(year, month)[1], 23, 59, 59),
        )
        count = sum(
            model.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
            ).count()
            for model in model_classes
        )
        result.append([f"{MONTH_NAMES[month - 1]} {year}", count])
    return result
