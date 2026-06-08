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

from analysis.models import GenericMeasurement, GrainSize, LuminescenceDating, RadiocarbonDating
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


def dashboard_callback(request, context):
    context.update(stat_data())
    return context


def stat_data():
    now = timezone.now()
    month_ago = now - timedelta(days=30)
    logger.debug("stat_data called at %s", now)

    # Pre-compute totals and percentage changes for dashboard metrics
    project_total = Project.objects.count()
    logger.debug("Project total: %s", project_total)
    project_last_month_count = Project.objects.filter(
        start_date__gte=month_ago,
        start_date__lt=now,
    ).count()
    project_last_month_pct = (
        round(project_last_month_count / project_total * 100, 2) if project_total > 0 else 0
    )
    logger.debug("Projects last month: %s", project_last_month_count)

    location_total = Location.objects.count()
    location_last_month_count = Location.objects.filter(
        created_at__gte=month_ago,
        created_at__lt=now,
    ).count()
    location_last_month_pct = (
        round(location_last_month_count / location_total * 100, 2) if location_total > 0 else 0
    )

    sample_total = Sample.objects.count()
    sample_last_month_count = Sample.objects.filter(
        created_at__gte=month_ago,
        created_at__lt=now,
    ).count()
    sample_last_month_pct = round(sample_last_month_count / sample_total * 100, 2) if sample_total > 0 else 0

    measurements_total = (
        GenericMeasurement.objects.count()
        + GrainSize.objects.count()
        + LuminescenceDating.objects.count()
        + RadiocarbonDating.objects.count()
    )
    measurements_last_month_count = (
        GenericMeasurement.objects.filter(
            created_at__gte=month_ago,
            created_at__lt=now,
        ).count()
        + GrainSize.objects.filter(
            created_at__gte=month_ago,
            created_at__lt=now,
        ).count()
        + LuminescenceDating.objects.filter(
            created_at__gte=month_ago,
            created_at__lt=now,
        ).count()
        + RadiocarbonDating.objects.filter(
            created_at__gte=month_ago,
            created_at__lt=now,
        ).count()
    )
    measurements_last_month_pct = (
        round(measurements_last_month_count / measurements_total * 100, 2) if measurements_total > 0 else 0
    )

    return {
        "project": [
            {
                "title": "Projects",
                "metric": f"{project_total}",
                "footer": mark_safe(
                    f'<strong class="text-green-700 font-semibold dark:text-green-400">+{intcomma(project_last_month_pct)}%</strong>&nbsp; last 30 days',
                ),
            },
            {
                "title": "Locations",
                "metric": f"{location_total}",
                "footer": mark_safe(
                    f'<strong class="text-green-700 font-semibold dark:text-green-400">+{intcomma(location_last_month_pct)}%</strong>&nbsp; last 30 days',
                ),
            },
            {
                "title": "Samples",
                "metric": f"{sample_total}",
                "footer": mark_safe(
                    f'<strong class="text-green-700 font-semibold dark:text-green-400">+{intcomma(sample_last_month_pct)}%</strong>&nbsp; last 30 days',
                ),
            },
            {
                "title": "Measurements",
                "metric": f"{measurements_total}",
                "footer": mark_safe(
                    f'<strong class="text-green-700 font-semibold dark:text-green-400">+{intcomma(measurements_last_month_pct)}%</strong>&nbsp; last 30 days',
                ),
            },
        ],
        "performance": [
            {
                "title": _("Sedimentological Measurements"),
                "metric": f"{GenericMeasurement.objects.count()+GrainSize.objects.count()}",
                "footer": mark_safe(
                    '<strong class="text-green-600 font-medium">+3.14%</strong>&nbsp;progress from last week',
                ),
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
                "metric": f"{LuminescenceDating.objects.count()+ RadiocarbonDating.objects.count()}",
                "footer": mark_safe(
                    '<strong class="text-green-600 font-medium">+3.14%</strong>&nbsp;progress from last week',
                ),
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
        end_date = make_aware(datetime(year, month, monthrange(year, month)[1], 23, 59, 59))
        count = sum(
            model.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
            for model in model_classes
        )
        result.append([f"{MONTH_NAMES[month - 1]} {year}", count])
    return result
