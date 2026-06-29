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


class ReferenceKeywordAdmin(ModelAdmin):
    """Admin for the ReferenceKeyword model."""

    change_form_show_cancel_button = True
    list_fullwidth = True
    list_display = ["keyword", "keyword_ger"]
    search_fields = ["keyword", "keyword_ger"]
    ordering = ["keyword"]


class ReferenceAdmin(ExportMixin, ModelAdmin):
    """Admin for the Reference model with tabbed fieldsets and custom list display."""

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
        entries: list[str] = []
        for ref in qs:
            entry_type = _BIBTEX_TYPE_MAP.get(ref.type, "misc")
            cite_key = (
                f"{ref.lead_author.last_name}{ref.year or 'unknown'}{ref.pk}"
            )
            author_names = [str(ref.lead_author)] + [
                str(a) for a in ref.second_author.all()
            ]
            field_lines = [
                f"  author = {{{' and '.join(author_names)}}}",
                f"  title = {{{ref.title}}}",
            ]
            if ref.year:
                field_lines.append(f"  year = {{{ref.year}}}")
            if ref.journal:
                field_lines.append(f"  journal = {{{ref.journal}}}")
            if ref.volume:
                field_lines.append(f"  volume = {{{ref.volume}}}")
            if ref.number:
                field_lines.append(f"  number = {{{ref.number}}}")
            if ref.pages:
                field_lines.append(f"  pages = {{{ref.pages}}}")
            if ref.publisher:
                field_lines.append(f"  publisher = {{{ref.publisher}}}")
            if ref.doi:
                field_lines.append(f"  doi = {{{ref.doi}}}")
            entries.append(
                f"@{entry_type}{{{cite_key},\n"
                + ",\n".join(field_lines)
                + "\n}"
            )
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

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Return the default queryset for the Reference changelist."""
        return super().get_queryset(request)

    def has_view_permission(
        self,
        _request: HttpRequest,
        _obj: Reference | None = None,
    ) -> bool:
        """Allow all authenticated users to view references."""
        return True

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: Reference | None = None,
    ) -> bool:
        """Allow change only when the user holds the per-object change permission."""
        if obj is None:
            return True
        change_perm = f"{self.opts.app_label}.change_{self.opts.model_name}"
        return request.user.has_perm(change_perm, obj)


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
