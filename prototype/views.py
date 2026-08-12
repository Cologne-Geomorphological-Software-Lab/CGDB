"""Views for the prototype app: documentation, dashboard, map, and GeoJSON endpoints."""

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import Count, Q, QuerySet
from django.db.models.functions import TruncMonth
from django.http import HttpRequest, HttpResponse
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
from field_data.models import Location, Sample
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


def map_dashboard(request: HttpRequest) -> HttpResponse:
    """Render the full-screen map dashboard page."""
    from django.contrib import admin as _admin

    from prototype.mixins import _addable_projects

    context = _admin.site.each_context(request)
    geojson_urls = {
        "locations": reverse("api_v1:location-map"),
        "study_areas": reverse("api_v1:studyarea-map"),
        "transects": reverse("api_v1:transect-map"),
        "landforms": reverse("api_v1:landform-list"),
    }
    context["geojson_urls"] = geojson_urls
    # Same check the admin layer already uses to decide add access
    # (ProjectBasedPermissionMixin.has_add_permission) — the edit toolbar
    # is only worth showing to users who could actually save anything.
    can_edit = (
        request.user.is_superuser or _addable_projects(request.user).exists()
    )
    context["map_config"] = {
        "geojsonUrls": geojson_urls,
        "wmsProxyUrl": reverse("wms_proxy"),
        "canEdit": can_edit,
    }
    # Also exposed as a plain context variable: {% if %} can't reach inside
    # map_config, which is only ever rendered as an opaque JSON blob for JS.
    context["can_edit"] = can_edit
    return render(request, "admin/map_dashboard.html", context)


_WMS_WHITELIST = ["services.bgr.de"]


@require_GET
def wms_proxy(request: HttpRequest) -> HttpResponse:
    """Server-side proxy for WMS GetFeatureInfo to avoid browser CORS restrictions."""
    url = request.GET.get("url", "")
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.scheme not in ("http", "https") or not any(
        host == w or host.endswith("." + w) for w in _WMS_WHITELIST
    ):
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

    context.update(
        stat_data(period_days, user=request.user if request else None)
    )
    context["filters"] = [
        {
            "title": _(p["label"]),
            "link": f"?period={p['days']}",
            "active": period_days == p["days"],
        }
        for p in _PERIOD_OPTIONS
    ]
    return context


def stat_data(period_days: int = 30, user: object = None) -> dict:
    """Compute dashboard statistics for the given time window in days.

    Architecture-review fix (F14): previously ran every query unfiltered,
    so any staff user (even one with zero project permissions) could infer
    the existence/scale of projects and data they can't otherwise see. When
    *user* is set and isn't a superuser, every query below is scoped to
    that user's accessible projects, matching the scoping already applied
    everywhere else in the admin/API (see prototype.mixins._accessible_projects).
    *user=None* (e.g. dashboard_callback's request=None case) is treated
    like a superuser — unscoped — since there's no user to scope against.
    """
    now = timezone.now()
    since = now - timedelta(days=period_days)
    logger.debug("stat_data called at %s (period=%d days)", now, period_days)

    scoped = user is not None and not getattr(user, "is_superuser", False)
    project_ids = (
        _accessible_projects(user).values_list("id", flat=True)
        if scoped
        else None
    )

    def _scope(queryset: QuerySet, project_lookup: str) -> QuerySet:
        """Restrict *queryset* to accessible projects, unless unscoped."""
        if project_ids is None:
            return queryset
        return queryset.filter(**{f"{project_lookup}__in": project_ids})

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
        _scope(Project.objects.all(), "id")
    )
    logger.debug("Project total: %s", project_total)

    # Locations — literature-sourced locations have no owning project, and
    # (like everywhere else this pattern appears) stay visible regardless.
    location_qs = Location.objects.all()
    if project_ids is not None:
        location_qs = location_qs.filter(
            Q(project_id__in=project_ids) | Q(data_source="literature")
        )
    location_total, location_period_count = _total_and_period(location_qs)

    # Samples — same literature exception as Location.
    sample_qs = Sample.objects.all()
    if project_ids is not None:
        sample_qs = sample_qs.filter(
            Q(project_id__in=project_ids)
            | Q(location__data_source="literature")
        )
    sample_total, sample_period_count = _total_and_period(sample_qs)

    # Measurements
    measurement_models = [
        GenericMeasurement,
        GrainSize,
        LuminescenceDating,
        RadiocarbonDating,
    ]
    measurement_totals = [
        _total_and_period(_scope(m.objects.all(), "sample__location__project"))
        for m in measurement_models
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
        location_qs.values("location_type")
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
    # Literature locations are visible to all staff regardless of project
    # scoping (see location_qs above) — literature_count intentionally
    # stays unscoped; only internal_count (project-owned data) is.
    literature_count = Location.objects.filter(
        data_source="literature"
    ).count()
    internal_count = _scope(
        Location.objects.filter(data_source="internal"), "project"
    ).count()

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
                                    "sample__location__project",
                                    project_ids,
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
                                    "sample__location__project",
                                    project_ids,
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
                                "data": _build_monthly_performance(
                                    [Sample], "project", project_ids
                                ),
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


def _build_monthly_performance(
    model_classes: list,
    project_lookup: str | None = None,
    project_ids: QuerySet | None = None,
) -> list:
    """Return a list of [month_label, count] pairs for the last 12 months.

    Uses one TruncMonth-grouped query per model instead of one .count() per
    month, so N models cost N queries total instead of 12*N. If
    *project_ids* is set, every model's queryset is additionally filtered
    via *project_lookup* (the field path from that model back to Project,
    e.g. "project" for Sample, "sample__location__project" for
    measurement models) — see stat_data's F14 fix.
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
        qs = model.objects.filter(created_at__gte=range_start)
        if project_ids is not None:
            qs = qs.filter(**{f"{project_lookup}__in": project_ids})
        rows = (
            qs.annotate(month=TruncMonth("created_at"))
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
