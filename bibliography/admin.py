from django.contrib import admin
from django.db.models import QuerySet
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeNumericFilter, RelatedDropdownFilter
from unfold.decorators import display

from .models import Author, Reference, ReferenceKeyword


class ReferenceKeywordAdmin(ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["keyword", "keyword_ger"]
    search_fields = ["keyword", "keyword_ger"]
    ordering = ["keyword"]


class ReferenceAdmin(ModelAdmin):
    change_form_show_cancel_button = True
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
    search_fields = ["title", "doi", "issn", "isbn_print", "lead_author__last_name"]
    list_display = [
        "lead_author",
        "year",
        "title",
        "colored_type",
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

    @display(
        label={
            "Paper": "success",
            "PhD thesis": "info",
            "Master's thesis": "warning",
            "Bachelor's thesis": "warning",
            "Monography": "default",
            "Chapter": "default",
            "Collection": "default",
        },
        description="Type",
    )
    def colored_type(self, obj) -> str:
        return obj.type

    def get_queryset(self, request) -> QuerySet:
        return super().get_queryset(request)

    def has_view_permission(self, request, obj=None) -> bool:
        return True

    def has_change_permission(self, request, obj=None) -> bool:
        if obj is None:
            return True
        change_perm = f"{self.opts.app_label}.change_{self.opts.model_name}"
        return request.user.has_perm(change_perm, obj)


class LeadAuthorReferenceInline(TabularInline):
    model = Reference
    fk_name = "lead_author"
    extra = 0
    fields = ["title", "year", "type"]
    show_change_link = True


class AuthorAdmin(ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["last_name", "first_name"]
    search_fields = ["last_name", "first_name"]
    ordering = ["last_name", "first_name"]
    fields = ["last_name", "first_name", "user"]
    inlines = [LeadAuthorReferenceInline]


admin.site.register(Reference, ReferenceAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(ReferenceKeyword, ReferenceKeywordAdmin)
