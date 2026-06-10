from __future__ import annotations

import re

from django.conf import settings
from django.http import HttpRequest
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

_UNSET = object()


def _sample_pk_from_request(request: HttpRequest) -> str | None:
    """Extract the current sample PK from the request URL context.

    Covers four cases:
    1. On the Sample changeform or custom sub-view: /admin/field_data/sample/<pk>/...
    2. On a measurement changelist/add form: ?sample__id__exact=<pk> or ?sample=<pk>
    3. On a measurement add form reached via "Add" button: ?_changelist_filters=sample__id__exact%3D<pk>
    4. On a measurement changeform: look up the FK via DB

    Result is cached on the request object so the 7 link functions (called once
    per tab render) do not each trigger a separate DB query.
    """
    cached = getattr(request, "_cgdb_sample_pk", _UNSET)
    if cached is not _UNSET:
        return cached

    result = _compute_sample_pk(request)
    request._cgdb_sample_pk = result
    return result


def _compute_sample_pk(request: HttpRequest) -> str | None:
    m = re.search(r"/field_data/sample/(\d+)/", request.path)
    if m:
        return m.group(1)

    from field_data.utils import extract_sample_pk_from_get

    pk = extract_sample_pk_from_get(request.GET)
    if pk:
        return pk

    for url_frag, model_name in (
        ("grainsize", "GrainSize"),
        ("luminescencedating", "LuminescenceDating"),
        ("radiocarbondating", "RadiocarbonDating"),
        ("counting", "Counting"),
        ("microxrfmeasurement", "MicroXRFMeasurement"),
        ("genericmeasurement", "GenericMeasurement"),
        ("cosmogenicnuclidedating", "CosmogenicNuclideDating"),
    ):
        m = re.search(rf"/analysis/{url_frag}/(\d+)/", request.path)
        if m:
            try:
                from django.apps import apps
                from django.core.exceptions import ObjectDoesNotExist

                obj = (
                    apps.get_model("analysis", model_name)
                    .objects.only("sample_id")
                    .get(pk=m.group(1))
                )
                return str(obj.sample_id)
            except (LookupError, ObjectDoesNotExist, ValueError):
                return None

    return None


def _sample_link(request: HttpRequest) -> str:
    pk = _sample_pk_from_request(request)
    if pk:
        return reverse("admin:field_data_sample_change", args=[pk])
    return reverse("admin:field_data_sample_changelist")


def _generic_measurement_link(request: HttpRequest) -> str:
    pk = _sample_pk_from_request(request)
    if pk:
        return reverse(
            "admin:field_data_sample_genericmeasurement",
            args=[pk],
        )
    return reverse("admin:analysis_genericmeasurement_changelist")


def _grainsize_link(request: HttpRequest) -> str:
    pk = _sample_pk_from_request(request)
    if pk:
        return reverse("admin:field_data_sample_grainsize", args=[pk])
    return reverse("admin:analysis_grainsize_changelist")


def _luminescence_link(request: HttpRequest) -> str:
    pk = _sample_pk_from_request(request)
    if pk:
        return reverse(
            "admin:field_data_sample_luminescencedating",
            args=[pk],
        )
    return reverse("admin:analysis_luminescencedating_changelist")


def _radiocarbon_link(request: HttpRequest) -> str:
    pk = _sample_pk_from_request(request)
    if pk:
        return reverse(
            "admin:field_data_sample_radiocarbondating",
            args=[pk],
        )
    return reverse("admin:analysis_radiocarbondating_changelist")


def _counting_link(request: HttpRequest) -> str:
    pk = _sample_pk_from_request(request)
    if pk:
        return reverse("admin:field_data_sample_counting", args=[pk])
    return reverse("admin:analysis_counting_changelist")


def _microxrf_link(request: HttpRequest) -> str:
    pk = _sample_pk_from_request(request)
    if pk:
        return reverse(
            "admin:field_data_sample_microxrfmeasurement",
            args=[pk],
        )
    return reverse("admin:analysis_microxrfmeasurement_changelist")


def _cosmogenic_link(request: HttpRequest) -> str:
    pk = _sample_pk_from_request(request)
    if pk:
        return reverse(
            "admin:field_data_sample_cosmogenicnuclidedating",
            args=[pk],
        )
    return reverse("admin:analysis_cosmogenicnuclidedating_changelist")


UNFOLD = {
    "SITE_HEADER": "CGDB Dashboard",
    "SITE_URL": "/",
    "SITE_LOGO": {
        "light": lambda _: static("logo/logo-light.png"),  # light mode
        "dark": lambda _: static("logo/logo-dark.png"),  # dark mode
    },
    "DASHBOARD_CALLBACK": "prototype.views.dashboard_callback",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda _: static("site/img/favicon-32x32.png"),
        },
    ],
    "SHOW_HISTORY": True,  # show/hide "History" button, default: True
    "SHOW_VIEW_ON_SITE": False,  # show/hide "View on site" button, default: True
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "6px",
    "COLORS": {
        "font": {
            "subtle-light": "var(--color-base-500)",
            "subtle-dark": "var(--color-base-400)",
            "default-light": "var(--color-base-600)",
            "default-dark": "var(--color-base-300)",
            "important-light": "var(--color-base-900)",
            "important-dark": "var(--color-base-100)",
        },
        "primary": {
            "50": "oklch(93.5% 0.028 205)",
            "100": "oklch(86.0% 0.040 210)",
            "200": "oklch(78.0% 0.060 210)",
            "300": "oklch(70.0% 0.075 215)",
            "400": "oklch(58.0% 0.088 230)",
            "500": "oklch(46.0% 0.090 230)",
            "600": "oklch(40.0% 0.100 235)",
            "700": "oklch(34.0% 0.100 245)",
            "800": "oklch(27.0% 0.090 250)",
            "900": "oklch(21.0% 0.080 255)",
            "950": "oklch(14.0% 0.070 260)",
        },
    },
    "SITE_DROPDOWN": [
        {
            "icon": "diamond",
            "title": _("Home"),
            "link": reverse_lazy("admin:index"),
        },
        {
            "icon": "diamond",
            "title": _("Data Orchestration"),
            "link": getattr(settings, "DAGSTER_URL", None),
        },
    ],
    "EXTENSIONS": {
        "modeltranslation": {
            "flags": {
                "en": "🇬🇧",
                "fr": "🇫🇷",
                "nl": "🇧🇪",
            },
        },
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "collapsible": False,
        "navigation": [
            {
                "title": _("Navigation"),
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": _("Projects"),
                        "icon": "workspaces",
                        "link": reverse_lazy(
                            "admin:prototype_project_changelist",
                        ),
                    },
                    {
                        "title": _("Literature"),
                        "icon": "menu_book",
                        "link": reverse_lazy(
                            "admin:bibliography_reference_changelist",
                        ),
                    },
                ],
            },
            {
                "title": _("Field Data"),
                "items": [
                    {
                        "title": _("Campaigns"),
                        "icon": "route",
                        "link": reverse_lazy(
                            "admin:field_data_campaign_changelist",
                        ),
                    },
                    {
                        "title": _("Study Areas"),
                        "icon": "hexagon",
                        "link": reverse_lazy(
                            "admin:field_data_studyarea_changelist",
                        ),
                    },
                    {
                        "title": _("Locations"),
                        "icon": "pin_drop",
                        "link": reverse_lazy(
                            "admin:field_data_location_changelist",
                        ),
                    },
                    {
                        "title": _("Samples"),
                        "icon": "total_dissolved_solids",
                        "link": reverse_lazy(
                            "admin:field_data_sample_changelist",
                        ),
                    },
                ],
            },
            {
                "title": _("Raw Data"),
                "items": [
                    {
                        "title": _("Raw Measurements"),
                        "icon": "storage",
                        "link": reverse_lazy(
                            "admin:analysis_rawmeasurement_changelist",
                        ),
                    },
                    {
                        "title": _("Raw Processings"),
                        "icon": "batch_prediction",
                        "link": reverse_lazy(
                            "admin:analysis_rawprocessing_changelist",
                        ),
                    },
                    {
                        "title": _("Algorithms"),
                        "icon": "code_blocks",
                        "link": reverse_lazy(
                            "admin:analysis_algorithm_changelist",
                        ),
                    },
                ],
            },
            {
                "title": _("Laboratory"),
                "items": [
                    {
                        "title": _("Devices"),
                        "icon": "precision_manufacturing",
                        "link": reverse_lazy(
                            "admin:laboratory_device_changelist",
                        ),
                    },
                    {
                        "title": _("Methods"),
                        "icon": "science",
                        "link": reverse_lazy(
                            "admin:laboratory_method_changelist",
                        ),
                    },
                    {
                        "title": _("Manufacturers"),
                        "icon": "business_center",
                        "link": reverse_lazy(
                            "admin:laboratory_manufacturer_changelist",
                        ),
                    },
                ],
            },
            {
                "title": _("Users & Groups"),
                "items": [
                    {
                        "title": _("Researchers"),
                        "icon": "school",
                        "link": reverse_lazy(
                            "admin:prototype_researcher_changelist",
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "auth.view_user",
                        ),
                    },
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy(
                            "admin:auth_user_changelist",
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "auth.view_user",
                        ),
                    },
                    {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": reverse_lazy(
                            "admin:auth_group_changelist",
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "auth.view_group",
                        ),
                    },
                ],
            },
        ],
    },
    "TABS": [
        {
            "models": [
                # Sample changeform
                {"name": "field_data.sample", "detail": True},
                # Analysis changelists (rendered by our custom Sample sub-views)
                "analysis.genericmeasurement",
                "analysis.grainsize",
                "analysis.luminescencedating",
                "analysis.radiocarbondating",
                "analysis.counting",
                "analysis.microxrfmeasurement",
                "analysis.cosmogenicnuclidedating",
                # Analysis changeforms (add/edit individual records)
                {"name": "analysis.genericmeasurement", "detail": True},
                {"name": "analysis.grainsize", "detail": True},
                {"name": "analysis.luminescencedating", "detail": True},
                {"name": "analysis.radiocarbondating", "detail": True},
                {"name": "analysis.counting", "detail": True},
                {
                    "name": "analysis.microxrfmeasurement",
                    "detail": True,
                },
                {
                    "name": "analysis.cosmogenicnuclidedating",
                    "detail": True,
                },
            ],
            "items": [
                {
                    "title": _("Sample"),
                    "link": _sample_link,
                    # Match only /field_data/sample/<pk>/change/ — not measurement sub-paths
                    "active": lambda request: bool(
                        re.search(
                            r"/field_data/sample/\d+/change/?$",
                            request.path,
                        ),
                    ),
                },
                {
                    "title": _("Generic Measurements"),
                    "link": _generic_measurement_link,
                    "active": lambda request: (
                        "/genericmeasurement/" in request.path
                    ),
                },
                {
                    "title": _("Grain Size"),
                    "link": _grainsize_link,
                    "active": lambda request: "/grainsize/" in request.path,
                },
                {
                    "title": _("Luminescence Dating"),
                    "link": _luminescence_link,
                    "active": lambda request: (
                        "/luminescencedating/" in request.path
                    ),
                },
                {
                    "title": _("Radiocarbon Dating"),
                    "link": _radiocarbon_link,
                    "active": lambda request: (
                        "/radiocarbondating/" in request.path
                    ),
                },
                {
                    "title": _("Pollen"),
                    "link": _counting_link,
                    "active": lambda request: "/counting/" in request.path,
                },
                {
                    "title": _("MicroXRF"),
                    "link": _microxrf_link,
                    "active": lambda request: (
                        "/microxrfmeasurement/" in request.path
                    ),
                },
                {
                    "title": _("Cosmogenic Nuclides"),
                    "link": _cosmogenic_link,
                    "active": lambda request: (
                        "/cosmogenicnuclidedating/" in request.path
                    ),
                },
            ],
        },
    ],
}

######################################################################
# Crispy forms
######################################################################

CRISPY_TEMPLATE_PACK = "unfold_crispy"

CRISPY_ALLOWED_TEMPLATE_PACKS = ["unfold_crispy"]


def environment_callback(_request: HttpRequest) -> list:
    """Callback has to return a list of two values representing text value and the color type of the label
    displayed in top right corner."""
    label = getattr(settings, "UNFOLD_ENVIRONMENT_LABEL", "Production")
    color = getattr(settings, "UNFOLD_ENVIRONMENT_COLOR", "danger")
    return [label, color]


def badge_callback(request: HttpRequest) -> int:
    """Return an integer badge value based on the current user.

    Currently this returns the number of permissions for authenticated users, or 0 for anonymous users.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return 0
    return len(user.get_all_permissions())


def permission_callback(request: HttpRequest) -> bool:
    return request.user.has_perm("prototype.change_project")
