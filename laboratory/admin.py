from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter

from .models import Accessory, AccessoryParameter, Calibration, Device, Firmware, Manufacturer, Method


class DeviceInline(TabularInline):
    model = Device
    extra = 0
    fields = ["name", "available"]
    show_change_link = True


class ManufacturerAdmin(ModelAdmin):
    list_display = ["name", "website"]
    search_fields = ["name"]
    ordering = ["name"]
    inlines = [DeviceInline]


class AccessoryInline(TabularInline):
    model = Accessory
    extra = 0
    fields = ["name"]
    show_change_link = True


class FirmwareInline(TabularInline):
    model = Firmware
    extra = 0
    fields = ["version", "installation_date"]
    show_change_link = True


class CalibrationInline(TabularInline):
    model = Calibration
    extra = 0
    fields = ["date", "researcher"]
    show_change_link = True


class DeviceAdmin(ModelAdmin):
    list_display = ["name", "manufacturer"]
    search_fields = ["name"]
    ordering = ["manufacturer__name", "name"]
    list_filter = [("manufacturer", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True
    inlines = [AccessoryInline, FirmwareInline, CalibrationInline]


class AccessoryParameterInline(TabularInline):
    model = AccessoryParameter


class AccessoryAdmin(ModelAdmin):
    list_display = ["device", "name"]
    search_fields = ["name", "device__name"]
    ordering = ["device__name", "name"]
    list_filter = [("device", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True
    inlines = [AccessoryParameterInline]


class FirmwareAdmin(ModelAdmin):
    list_display = ["device", "version", "installation_date"]
    search_fields = ["device__name", "version"]
    ordering = ["device__name", "-installation_date"]
    list_filter = [("device", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True


class CalibrationAdmin(ModelAdmin):
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
    list_display = ["name", "category", "device", "laboratory"]
    search_fields = ["name", "token"]
    ordering = ["name"]
    list_filter = [
        ("category", ChoicesDropdownFilter),
        ("device", RelatedDropdownFilter),
        ("laboratory", ChoicesDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True


admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(Device, DeviceAdmin)
admin.site.register(Method, MethodAdmin)
admin.site.register(Calibration, CalibrationAdmin)
admin.site.register(Firmware, FirmwareAdmin)
admin.site.register(Accessory, AccessoryAdmin)
