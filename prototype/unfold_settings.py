from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_HEADER": "CGDB Dashboard",
    "SITE_URL": "/",
    "SITE_LOGO": {
        "light": lambda request: static("logo/logo-light.png"),  # light mode
        "dark": lambda request: static("logo/logo-dark.png"),  # dark mode
    },
    "DASHBOARD_CALLBACK": "prototype.views.dashboard_callback",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("site/img/favicon-32x32.png"),
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
                        "title": _("Map"),
                        "icon": "map",
                        "link": "/map/",
                    },
                    {
                        "title": _("Projects"),
                        "icon": "workspaces",
                        "link": reverse_lazy("admin:prototype_project_changelist"),
                    },
                    {
                        "title": _("Literature"),
                        "icon": "menu_book",
                        "link": reverse_lazy("admin:bibliography_reference_changelist"),
                    },
                ],
            },
            {
                "title": _("Field Data"),
                "items": [
                    {
                        "title": _("Campaigns"),
                        "icon": "route",
                        "link": reverse_lazy("admin:field_data_campaign_changelist"),
                    },
                    {
                        "title": _("Study Areas"),
                        "icon": "hexagon",
                        "link": reverse_lazy("admin:field_data_studyarea_changelist"),
                    },
                    {
                        "title": _("Locations"),
                        "icon": "pin_drop",
                        "link": reverse_lazy("admin:field_data_location_changelist"),
                    },
                    {
                        "title": _("Samples"),
                        "icon": "total_dissolved_solids",
                        "link": reverse_lazy("admin:field_data_sample_changelist"),
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
                        "link": reverse_lazy("admin:analysis_rawprocessing_changelist"),
                    },
                    {
                        "title": _("Algorithms"),
                        "icon": "code_blocks",
                        "link": reverse_lazy("admin:analysis_algorithm_changelist"),
                    },
                ],
            },
            {
                "title": _("Analyses"),
                "items": [
                    {
                        "title": _("Generic Measurements"),
                        "icon": "experiment",
                        "link": reverse_lazy(
                            "admin:analysis_genericmeasurement_changelist",
                        ),
                    },
                    {
                        "title": _("Grain sizes"),
                        "icon": "grain",
                        "link": reverse_lazy("admin:analysis_grainsize_changelist"),
                    },
                    {
                        "title": _("MicroXRF"),
                        "icon": "process_chart",
                        "link": reverse_lazy(
                            "admin:analysis_microxrfmeasurement_changelist",
                        ),
                    },
                    {
                        "title": _("Pollen"),
                        "icon": "nature",
                        "link": reverse_lazy("admin:analysis_counting_changelist"),
                    },
                    {
                        "title": _("Luminescence"),
                        "icon": "brightness_7",
                        "link": reverse_lazy(
                            "admin:analysis_luminescencedating_changelist",
                        ),
                    },
                    {
                        "title": _("Radiocarbon"),
                        "icon": "schedule",
                        "link": reverse_lazy(
                            "admin:analysis_radiocarbondating_changelist",
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
                        "link": reverse_lazy("admin:laboratory_device_changelist"),
                    },
                    {
                        "title": _("Accessories"),
                        "icon": "rule_settings",
                        "link": reverse_lazy("admin:laboratory_accessory_changelist"),
                    },
                    {
                        "title": _("Methods"),
                        "icon": "science",
                        "link": reverse_lazy("admin:laboratory_method_changelist"),
                    },
                    {
                        "title": _("Manufacturers"),
                        "icon": "business_center",
                        "link": reverse_lazy(
                            "admin:laboratory_manufacturer_changelist",
                        ),
                    },
                    {
                        "title": _("Calibrations"),
                        "icon": "track_changes",
                        "link": reverse_lazy("admin:laboratory_calibration_changelist"),
                    },
                    {
                        "title": _("Firmwares"),
                        "icon": "memory",
                        "link": reverse_lazy("admin:laboratory_firmware_changelist"),
                    },
                ],
            },
            {
                "title": _("Morphogrid"),
                "items": [
                    {
                        "title": _("Grid cells"),
                        "icon": "person",
                        "link": reverse_lazy("admin:morphogrid_gridcell_changelist"),
                        "permission": lambda request: request.user.has_perm(
                            "auth.view_user"
                        ),
                    },
                    {
                        "title": _("Datacubes"),
                        "icon": "person",
                        "link": reverse_lazy("admin:morphogrid_datacube_changelist"),
                        "permission": lambda request: request.user.has_perm(
                            "auth.view_user"
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
                        "link": reverse_lazy("admin:prototype_researcher_changelist"),
                        "permission": lambda request: request.user.has_perm(
                            "auth.view_user"
                        ),
                    },
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        "permission": lambda request: request.user.has_perm(
                            "auth.view_user"
                        ),
                    },
                    {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permission": lambda request: request.user.has_perm(
                            "auth.view_group"
                        ),
                    },
                ],
            },
        ],
    },
}

######################################################################
# Crispy forms
######################################################################

CRISPY_TEMPLATE_PACK = "unfold_crispy"

CRISPY_ALLOWED_TEMPLATE_PACKS = ["unfold_crispy"]


def environment_callback(request):
    """Callback has to return a list of two values representing text value and the color type of the label
    displayed in top right corner."""
    label = getattr(settings, "UNFOLD_ENVIRONMENT_LABEL", "Production")
    color = getattr(settings, "UNFOLD_ENVIRONMENT_COLOR", "danger")
    return [label, color]


def badge_callback(request):
    """Return an integer badge value based on the current user.

    Currently this returns the number of permissions for authenticated users, or 0 for anonymous users.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return 0
    return len(user.get_all_permissions())


def permission_callback(request):
    return request.user.has_perm("prototype.change_project")
