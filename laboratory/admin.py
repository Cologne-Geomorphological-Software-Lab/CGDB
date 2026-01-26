from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter

from .models import Accessory, AccessoryParameter, Calibration, Device, Firmware, Manufacturer, Method


class ManufacturerAdmin(ModelAdmin):
    list_display = [
        "name",
        "website",
    ]


class DeviceAdmin(ModelAdmin):
    list_display = [
        "name",
        "manufacturer",
    ]


class AccessoryParameterInline(TabularInline):
    model = AccessoryParameter


class AccessoryAdmin(ModelAdmin):
    list_display = [
        "device",
        "name",
    ]
    inlines = [AccessoryParameterInline]


class FirmwareAdmin(ModelAdmin):
    list_display = [
        "device",
        "version",
        "installation_date",
    ]


class CalibrationAdmin(ModelAdmin):
    list_display = [
        "device",
        "date",
        "researcher",
    ]


class MethodAdmin(ModelAdmin):
    list_display = [
        "name",
        "category",
        "device",
        "laboratory",
    ]
    list_filter = [
        (
            "category",
            ChoicesDropdownFilter,
        ),
        (
            "device",
            RelatedDropdownFilter,
        ),
        (
            "laboratory",
            ChoicesDropdownFilter,
        ),
    ]
    list_filter_sheet = False
    list_filter_submit = True


admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(Device, DeviceAdmin)
admin.site.register(Method, MethodAdmin)
admin.site.register(Calibration, CalibrationAdmin)
admin.site.register(Firmware, FirmwareAdmin)
admin.site.register(Accessory, AccessoryAdmin)
