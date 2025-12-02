from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeNumericFilter,
    RelatedDropdownFilter,
)

from .models import Author, Reference, ReferenceKeyword


class ReferenceKeywordAdmin(ModelAdmin):
    pass


class ReferenceAdmin(ModelAdmin):
    fieldsets = [
        (
            "General Information",
            {
                "classes": ["tab"],
                "fields": (
                    "title",
                    "year",
                    "published",
                    "type",
                    "project",
                ),
            },
        ),
        (
            "Authors & Supervision",
            {
                "classes": ["tab"],
                "fields": (
                    "lead_author",
                    "second_author",
                    "supervisor",
                ),
            },
        ),
        (
            "Content",
            {
                "classes": ["tab"],
                "fields": (
                    "abstract",
                    "keywords",
                    "how_to_cite",
                ),
            },
        ),
        (
            "Publication Details",
            {
                "classes": ["tab"],
                "fields": (
                    "journal",
                    "volume",
                    "number",
                    "pages",
                    "parent_publication",
                    "publisher",
                    "location_of_publication",
                ),
            },
        ),
        (
            "Identifiers",
            {
                "classes": ["tab"],
                "fields": (
                    "doi",
                    "issn",
                    "isbn_print",
                    "isbn_online",
                ),
            },
        ),
    ]
    filter_horizontal = ["second_author", "supervisor", "keywords"]
    list_display = [
        "lead_author",
        "year",
        "title",
    ]
    list_filter = [
        ("type", ChoicesDropdownFilter),
        ("lead_author", RelatedDropdownFilter),
        ("year", RangeNumericFilter),
        ("published", ChoicesDropdownFilter),
        ("project", RelatedDropdownFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True

    def get_queryset(self, request):
        qs = self.model._default_manager.all()
        return qs

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        change_perm = f"{self.opts.app_label}.change_{self.opts.model_name}"
        return request.user.has_perm(change_perm, obj)


class AuthorAdmin(ModelAdmin):
    list_display = [
        "last_name",
        "first_name",
    ]
    fields = [
        "last_name",
        "first_name",
        "user",
    ]


admin.site.register(Reference, ReferenceAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(ReferenceKeyword, ReferenceKeywordAdmin)
