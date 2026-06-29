"""Admin configuration for the laboratory app."""

from __future__ import annotations

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import display

from .models import (
    Accessory,
    AccessoryParameter,
    Calibration,
    Device,
    Firmware,
    Manufacturer,
    Method,
)


class DeviceInline(TabularInline):
    """Inline editor for devices within a manufacturer."""

    model = Device
    extra = 0
    fields = ["name"]
    show_change_link = True


class ManufacturerAdmin(ModelAdmin):
    """Admin interface for manufacturers."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = ["name", "website"]
    search_fields = ["name"]
    ordering = ["name"]
    list_filter_sheet = False
    list_filter_submit = True
    inlines = [DeviceInline]


class AccessoryInline(TabularInline):
    """Inline editor for accessories within a device."""

    model = Accessory
    extra = 0
    fields = ["name"]
    show_change_link = True


class FirmwareInline(TabularInline):
    """Inline editor for firmware versions within a device."""

    model = Firmware
    extra = 0
    fields = ["version", "installation_date"]
    show_change_link = True


class CalibrationInline(TabularInline):
    """Inline editor for calibration records within a device."""

    model = Calibration
    extra = 0
    fields = ["date", "researcher"]
    show_change_link = True


class DeviceAdmin(ModelAdmin):
    """Admin interface for devices."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = ["name", "manufacturer"]
    search_fields = ["name"]
    ordering = ["manufacturer__name", "name"]
    list_filter = [("manufacturer", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True
    inlines = [AccessoryInline, FirmwareInline, CalibrationInline]


class AccessoryParameterInline(TabularInline):
    """Inline editor for accessory parameters within an accessory."""

    model = AccessoryParameter
    extra = 0
    fields = ["method", "parameter_name", "parameter_value", "parameter_unit"]


class AccessoryAdmin(ModelAdmin):
    """Admin interface for accessories."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = ["device", "name"]
    search_fields = ["name", "device__name"]
    ordering = ["device__name", "name"]
    list_filter = [("device", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True
    inlines = [AccessoryParameterInline]


class FirmwareAdmin(ModelAdmin):
    """Admin interface for firmware records."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = ["device", "version", "installation_date"]
    search_fields = ["device__name", "version"]
    ordering = ["device__name", "-installation_date"]
    list_filter = [("device", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True


class CalibrationAdmin(ModelAdmin):
    """Admin interface for calibration records."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = ["device", "date", "researcher"]
    search_fields = ["device__name"]
    ordering = ["device__name", "-date"]
    list_filter = [
        ("device", RelatedDropdownFilter),
        ("researcher", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True


class MethodAdmin(ModelAdmin):
    """Admin interface for analytical methods."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = ["name", "colored_category", "device", "laboratory"]
    search_fields = ["name", "token"]
    ordering = ["name"]
    list_filter = [
        ("category", ChoicesDropdownFilter),
        ("device", RelatedDropdownFilter),
        ("laboratory", ChoicesDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True

    @display(
        label={"CHEM": "success", "PHY": "info", "CHRO": "warning"},
        description="Category",
    )
    def colored_category(self, obj: Method) -> str:
        """Return the category value for colour-coded display."""
        return obj.category


admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(Device, DeviceAdmin)
admin.site.register(Method, MethodAdmin)
admin.site.register(Calibration, CalibrationAdmin)
admin.site.register(Firmware, FirmwareAdmin)
admin.site.register(Accessory, AccessoryAdmin)
