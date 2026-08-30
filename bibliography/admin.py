"""Django admin configuration for the bibliography app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin
from django.http import HttpResponse
from import_export.admin import ExportMixin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeNumericFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import display

from prototype.mixins import CreatorScopedEditMixin

from .models import Author, Reference, ReferenceKeyword
from .resources import AuthorResource, ReferenceResource

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


_BIBTEX_TYPE_MAP: dict[str, str] = {
    "Paper": "article",
    "Monography": "book",
    "Chapter": "incollection",
    "Collection": "book",
    "PhD thesis": "phdthesis",
    "Master's thesis": "mastersthesis",
    "Bachelor's thesis": "mastersthesis",
}

# Reference attributes to emit as BibTeX fields when present, in order.
_BIBTEX_OPTIONAL_FIELDS = (
    "year",
    "journal",
    "volume",
    "number",
    "pages",
    "publisher",
    "doi",
)


def _bibtex_entry(ref: Reference) -> str:
    """Return one BibTeX entry (@type{key, field = {...}, ...}) for a Reference."""
    entry_type = _BIBTEX_TYPE_MAP.get(ref.type, "misc")
    cite_key = f"{ref.lead_author.last_name}{ref.year or 'unknown'}{ref.pk}"
    author_names = [str(ref.lead_author)] + [
        str(a) for a in ref.second_author.all()
    ]
    field_lines = [
        f"  author = {{{' and '.join(author_names)}}}",
        f"  title = {{{ref.title}}}",
    ]
    for field in _BIBTEX_OPTIONAL_FIELDS:
        value = getattr(ref, field)
        if value:
            field_lines.append(f"  {field} = {{{value}}}")
    return f"@{entry_type}{{{cite_key},\n" + ",\n".join(field_lines) + "\n}"


class ReferenceKeywordAdmin(ModelAdmin):
    """Admin for the ReferenceKeyword model."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = ["keyword", "keyword_ger"]
    search_fields = ["keyword", "keyword_ger"]
    ordering = ["keyword"]


class ReferenceAdmin(CreatorScopedEditMixin, ExportMixin, ModelAdmin):
    """Admin for the Reference model with tabbed fieldsets and custom list display.

    tech debt LBG4: laboratory/geodata's admins use plain staff/model-level
    permissions because their catalogs (devices, methods, landform regions)
    have no natural per-object owner. Reference is different - it's a
    shared, publicly-browsable catalog (has_view_permission below is
    intentionally open to all staff) where only the permission holder
    should be able to change or delete an entry (tech debt LBG17), hence
    CreatorScopedEditMixin instead of either extreme.
    """

    resource_classes = [ReferenceResource]
    change_form_show_cancel_button = True
    list_fullwidth = True
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
    search_fields = [
        "title",
        "doi",
        "issn",
        "isbn_print",
        "lead_author__last_name",
    ]
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
    actions = ["export_as_bibtex"]

    def export_as_bibtex(
        self, _request: HttpRequest, queryset: QuerySet
    ) -> HttpResponse:
        """Export the selected references as a BibTeX .bib file."""
        qs = queryset.select_related("lead_author").prefetch_related(
            "second_author"
        )
        entries = [_bibtex_entry(ref) for ref in qs]
        response = HttpResponse(
            "\n\n".join(entries), content_type="application/x-bibtex"
        )
        response["Content-Disposition"] = (
            'attachment; filename="references.bib"'
        )
        return response

    export_as_bibtex.short_description = "Export selected as BibTeX (.bib)"  # type: ignore[attr-defined]

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
    def colored_type(self, obj: Reference) -> str:
        """Return the reference type value used to render a coloured badge."""
        return obj.type

    def has_view_permission(
        self,
        _request: HttpRequest,
        _obj: Reference | None = None,
    ) -> bool:
        """Allow all authenticated users to view references."""
        return True

    # has_change_permission / has_delete_permission: see CreatorScopedEditMixin.


class LeadAuthorReferenceInline(TabularInline):
    """Inline showing references where this author is the lead author."""

    model = Reference
    fk_name = "lead_author"
    extra = 0
    fields = ["title", "year", "type"]
    show_change_link = True


class AuthorAdmin(ExportMixin, ModelAdmin):
    """Admin for the Author model with an inline of their lead-author references."""

    resource_classes = [AuthorResource]
    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = ["last_name", "first_name"]
    search_fields = ["last_name", "first_name"]
    ordering = ["last_name", "first_name"]
    fields = ["last_name", "first_name", "user"]
    inlines = [LeadAuthorReferenceInline]


admin.site.register(Reference, ReferenceAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(ReferenceKeyword, ReferenceKeywordAdmin)
