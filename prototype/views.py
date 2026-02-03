import json
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
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from analysis.models import GenericMeasurement, GrainSize, LuminescenceDating, RadiocarbonDating
from field_data.models import Location, Sample
from prototype.models import Project


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
    print("Month: " + str(month_ago))

    # Pre-compute totals and percentage changes for dashboard metrics
    project_total = Project.objects.count()
    print("Projects: " + str(project_total))
    project_last_month_count = Project.objects.filter(
        start_date__gte=month_ago,
        start_date__lt=now,
    ).count()
    project_last_month_pct = (
        round(project_last_month_count / project_total * 100, 2) if project_total > 0 else 0
    )

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
        "navigation": [
            {"title": _("Dashboard"), "link": "/", "active": True},
            {"title": _("Tools"), "link": "#"},
        ],
        "filters": [
            {
                "title": _("All"),
                "link": "#",
                "active": True,
            },
            {
                "title": _("Mine"),
                "link": "#",
            },
        ],
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
                                "data": sed_performance,
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
                                "data": geoch_performance,
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

performance = []
geoch_performance = []
sed_performance = []
today = now()

for i in range(11, -1, -1):
    month_date = today - relativedelta(months=i)
    year = month_date.year
    month = month_date.month

    start_date = datetime(year, month, 1)
    end_day = monthrange(year, month)[1]
    end_date = datetime(year, month, end_day, 23, 59, 59)

    count = Location.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date,
    ).count()

    performance.append([f"{MONTH_NAMES[month - 1]} {year}", count])

    # Platzhalter
    geoch_performance.append(
        [
            f"{MONTH_NAMES[month - 1]} {year}",
            LuminescenceDating.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
            ).count()
            + RadiocarbonDating.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
            ).count(),
        ],
    )
    sed_performance.append(
        [
            f"{MONTH_NAMES[month - 1]} {year}",
            GenericMeasurement.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
            ).count()
            + GrainSize.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
            ).count(),
        ],
    )
