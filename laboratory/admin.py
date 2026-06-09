from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter
from unfold.decorators import display

from .models import Accessory, AccessoryParameter, Calibration, Device, Firmware, Manufacturer, Method


class DeviceInline(TabularInline):
    model = Device
    extra = 0
    fields = ["name", "available"]
    show_change_link = True


class ManufacturerAdmin(ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["name", "website"]
    search_fields = ["name"]
    ordering = ["name"]
    list_filter_sheet = False
    list_filter_submit = True
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
    change_form_show_cancel_button = True
    list_display = ["name", "manufacturer"]
    search_fields = ["name"]
    ordering = ["manufacturer__name", "name"]
    list_filter = [("manufacturer", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True
    inlines = [AccessoryInline, FirmwareInline, CalibrationInline]


class AccessoryParameterInline(TabularInline):
    model = AccessoryParameter
    extra = 0
    fields = ["method", "parameter_name", "parameter_value", "parameter_unit"]


class AccessoryAdmin(ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["device", "name"]
    search_fields = ["name", "device__name"]
    ordering = ["device__name", "name"]
    list_filter = [("device", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True
    inlines = [AccessoryParameterInline]


class FirmwareAdmin(ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["device", "version", "installation_date"]
    search_fields = ["device__name", "version"]
    ordering = ["device__name", "-installation_date"]
    list_filter = [("device", RelatedDropdownFilter)]
    list_filter_sheet = False
    list_filter_submit = True


class CalibrationAdmin(ModelAdmin):
    change_form_show_cancel_button = True
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
    change_form_show_cancel_button = True
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
    def colored_category(self, obj):
        return obj.category


admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(Device, DeviceAdmin)
admin.site.register(Method, MethodAdmin)
admin.site.register(Calibration, CalibrationAdmin)
admin.site.register(Firmware, FirmwareAdmin)
admin.site.register(Accessory, AccessoryAdmin)
