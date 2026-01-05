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
    "COLORS": {
        "font": {
            "subtle-light": "107 114 128",
            "subtle-dark": "156 163 175",
            "default-light": "0 81 118",
            "default-dark": "209 213 219",
            "important-light": "0 81 118",
            "important-dark": "234 86 79",
        },
        "primary": {
            "50": "224 240 245",
            "100": "190 220 230",
            "200": "150 200 215",
            "300": "110 175 200",
            "400": "70 140 175",
            "500": "40 110 150",
            "600": "25 95 140",
            "700": "15 75 120",
            "800": "10 60 100",
            "900": "5 45 80",
            "950": "0 30 60",
        },
    },
    "STYLES": [
        lambda request: static("css/styles.css"),
    ],
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
        "show_search": True,
        "show_all_applications": True,
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
                "collapsible": True,
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
                "collapsible": True,
                "items": [
                    {
                        "title": _("Raw Measurements"),
                        "icon": "storage",
                        "link": reverse_lazy(
                            "admin:analysis_rawmeasurement_changelist"
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
                "collapsible": True,
                "items": [
                    {
                        "title": _("Generic Measurements"),
                        "icon": "experiment",
                        "link": reverse_lazy(
                            "admin:analysis_genericmeasurement_changelist"
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
                            "admin:analysis_microxrfmeasurement_changelist"
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
                            "admin:analysis_luminescencedating_changelist"
                        ),
                    },
                    {
                        "title": _("Radiocarbon"),
                        "icon": "schedule",
                        "link": reverse_lazy(
                            "admin:analysis_radiocarbondating_changelist"
                        ),
                    },
                ],
            },
            {
                "title": _("Laboratory"),
                "collapsible": True,
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
                            "admin:laboratory_manufacturer_changelist"
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
                "title": _("Users & Groups"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        "permissions": ["auth.view_user"],
                    },
                    {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permissions": ["auth.view_user"],
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
    """Callback has to return a list of two values represeting text value and the color type of the label
    displayed in top right corner."""
    return ["Production", "danger"]


def badge_callback(request):
    return 3


def permission_callback(request):
    return request.user.has_perm("sample_app.change_model")
