from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import CubeLayer, DataCube, GridCell


# --- Inlines ---
class CubeLayerInline(TabularInline):
    model = CubeLayer
    extra = 0
    fields = ("layer_type", "acquisition_date", "created_at")
    readonly_fields = ["created_at"]


# --- Admins ---
@admin.register(GridCell)
class GridCellAdmin(ModelAdmin):
    change_form_template = "admin/morphogrid/gridcell/change_form.html"
    list_display = ("grid_id", "s2_level", "s2_token", "created_at")
    search_fields = ("grid_id", "s2_token")
    list_filter = ("s2_level",)
    readonly_fields = ("created_at", "modified_at")
    fieldsets = (
        ("Grid Information", {"fields": ("grid_id", "s2_token", "s2_level")}),
        ("Metadata", {"fields": ("created_at", "modified_at"), "classes": ("collapse",)}),
    )


@admin.register(DataCube)
class DataCubeAdmin(ModelAdmin):
    list_display = ("cell", "layer_count", "created_at", "modified_at")
    search_fields = ("cell__grid_id",)
    readonly_fields = ("created_at", "modified_at")
    list_per_page = 50
    raw_id_fields = ["cell"]
    inlines = [CubeLayerInline]

    def layer_count(self, obj):
        return obj.layers.count()

    layer_count.short_description = "Layers"
    layer_count.admin_order_field = "layer_count"
