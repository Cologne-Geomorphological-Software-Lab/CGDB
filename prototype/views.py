import json
import os
from calendar import monthrange
from datetime import datetime, timedelta
from functools import lru_cache

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
    return render(request, "docmentation.html", {"filepath": f"/static/docs/{filepath}"})


def logout_view(request):
    logout(request)
    return redirect("/")


def dashboard_callback(request, context):
    context.update(stat_data())
    return context


@lru_cache
def stat_data():
    now = timezone.now()
    start_of_this_month = now.replace(day=1)
    end_of_last_month = start_of_this_month - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)

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
                "metric": f"{Project.objects.count()}",
                "footer": mark_safe(
                    f'<strong class="text-green-700 font-semibold dark:text-green-400">+{intcomma(round(Project.objects.filter(start_date__gte=start_of_last_month,start_date__lt=start_of_this_month).count() / Project.objects.count() * 100, 2) if Project.objects.count() > 0 else 0)}%</strong>&nbsp; last month',
                ),
            },
            {
                "title": "Locations",
                "metric": f"{Location.objects.count()}",
                "footer": mark_safe(
                    f'<strong class="text-green-700 font-semibold dark:text-green-400">+{intcomma(round(Location.objects.filter(created_at__gte=start_of_last_month,created_at__lt=start_of_this_month).count() / Location.objects.count() * 100, 2) if Location.objects.count() > 0 else 0)}%</strong>&nbsp; last month',
                ),
            },
            {
                "title": "Samples",
                "metric": f"{Sample.objects.count()}",
                "footer": mark_safe(
                    f'<strong class="text-green-700 font-semibold dark:text-green-400">+{intcomma(round(Sample.objects.filter(created_at__gte=start_of_last_month,created_at__lt=start_of_this_month).count() / Sample.objects.count() * 100, 2) if Sample.objects.count() > 0 else 0)}%</strong>&nbsp; last month',
                ),
            },
            {
                "title": "Measurements",
                "metric": f"{GenericMeasurement.objects.count()+GrainSize.objects.count()+LuminescenceDating.objects.count()+RadiocarbonDating.objects.count()}",
                "footer": mark_safe(
                    f'<strong class="text-green-700 font-semibold dark:text-green-400">+{intcomma(round((GenericMeasurement.objects.filter(created_at__gte=start_of_last_month,created_at__lt=start_of_this_month).count()+GrainSize.objects.filter(created_at__gte=start_of_last_month,created_at__lt=start_of_this_month).count()+LuminescenceDating.objects.filter(created_at__gte=start_of_last_month,created_at__lt=start_of_this_month).count()+RadiocarbonDating.objects.filter(created_at__gte=start_of_last_month,created_at__lt=start_of_this_month).count()) / (GenericMeasurement.objects.count()+GrainSize.objects.count()+LuminescenceDating.objects.count()+RadiocarbonDating.objects.count()) * 100, 2) if (GenericMeasurement.objects.count()+GrainSize.objects.count()+LuminescenceDating.objects.count()+RadiocarbonDating.objects.count()) > 0 else 0)}%</strong>&nbsp; last month',
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

    count = Location.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()

    performance.append([f"{MONTH_NAMES[month - 1]} {year}", count])

    # Platzhalter
    geoch_performance.append(
        [
            f"{MONTH_NAMES[month - 1]} {year}",
            LuminescenceDating.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
            + RadiocarbonDating.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count(),
        ],
    )
    sed_performance.append(
        [
            f"{MONTH_NAMES[month - 1]} {year}",
            GenericMeasurement.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
            + GrainSize.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count(),
        ],
    )
