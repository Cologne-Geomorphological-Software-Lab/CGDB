import json
import logging
import os
from calendar import monthrange
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.humanize.templatetags.humanize import intcomma
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.timezone import make_aware, now
from django.utils.translation import gettext_lazy as _

from analysis.models import (
    GenericMeasurement,
    GrainSize,
    LuminescenceDating,
    RadiocarbonDating,
)
from field_data.models import Location, Sample
from prototype.models import Project

logger = logging.getLogger(__name__)


def documentation(request, filepath):
    doc_path = os.path.join(settings.BASE_DIR, "static", "docs", filepath)
    if not os.path.exists(doc_path):
        return render(request, "404.html", status=404)
    return render(
        request,
        "documentation.html",
        {"filepath": f"/static/docs/{filepath}"},
    )


def logout_view(request):
    logout(request)
    return redirect("/")


_PERIOD_OPTIONS = [
    {"days": 30, "label": "30 days"},
    {"days": 90, "label": "90 days"},
    {"days": 365, "label": "1 year"},
]


def dashboard_callback(request, context):
    try:
        period_days = int(request.GET.get("period", 30))
    except (ValueError, TypeError):
        period_days = 30
    if period_days not in {p["days"] for p in _PERIOD_OPTIONS}:
        period_days = 30

    context.update(stat_data(period_days))
    context["navigation"] = [
        {
            "title": _("Overview"),
            "link": "/",
            "active": True,
        },
    ]
    context["filters"] = [
        {
            "title": _(p["label"]),
            "link": f"?period={p['days']}",
            "active": period_days == p["days"],
        }
        for p in _PERIOD_OPTIONS
    ]
    return context


def stat_data(period_days: int = 30):
    now = timezone.now()
    since = now - timedelta(days=period_days)
    logger.debug("stat_data called at %s (period=%d days)", now, period_days)

    def _pct(count, total):
        return round(count / total * 100, 2) if total > 0 else 0

    def _footer(pct, period_days):
        return mark_safe(
            f'<strong class="text-green-700 font-semibold dark:text-green-400">'
            f"+{intcomma(pct)}%</strong>&nbsp; last {period_days} days"
        )

    # Projects
    project_total = Project.objects.count()
    project_period_count = Project.objects.filter(start_date__gte=since, start_date__lt=now).count()
    logger.debug("Project total: %s", project_total)

    # Locations
    location_total = Location.objects.count()
    location_period_count = Location.objects.filter(created_at__gte=since, created_at__lt=now).count()

    # Samples
    sample_total = Sample.objects.count()
    sample_period_count = Sample.objects.filter(created_at__gte=since, created_at__lt=now).count()

    # Measurements
    measurement_models = [GenericMeasurement, GrainSize, LuminescenceDating, RadiocarbonDating]
    measurements_total = sum(m.objects.count() for m in measurement_models)
    measurements_period_count = sum(
        m.objects.filter(created_at__gte=since, created_at__lt=now).count()
        for m in measurement_models
    )

    return {
        "project": [
            {
                "title": "Projects",
                "metric": f"{project_total}",
                "footer": _footer(_pct(project_period_count, project_total), period_days),
            },
            {
                "title": "Locations",
                "metric": f"{location_total}",
                "footer": _footer(_pct(location_period_count, location_total), period_days),
            },
            {
                "title": "Samples",
                "metric": f"{sample_total}",
                "footer": _footer(_pct(sample_period_count, sample_total), period_days),
            },
            {
                "title": "Measurements",
                "metric": f"{measurements_total}",
                "footer": _footer(_pct(measurements_period_count, measurements_total), period_days),
            },
        ],
        "performance": [
            {
                "title": _("Sedimentological Measurements"),
                "metric": f"{GenericMeasurement.objects.count() + GrainSize.objects.count()}",
                "chart": json.dumps(
                    {
                        "datasets": [
                            {
                                "data": _build_monthly_performance([GenericMeasurement, GrainSize]),
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
                                "data": _build_monthly_performance([LuminescenceDating, RadiocarbonDating]),
                                "borderColor": "var(--color-primary-300)",
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
            datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
        )
        count = sum(
            model.objects.filter(
                created_at__gte=start_date, created_at__lte=end_date
            ).count()
            for model in model_classes
        )
        result.append([f"{MONTH_NAMES[month - 1]} {year}", count])
    return result
