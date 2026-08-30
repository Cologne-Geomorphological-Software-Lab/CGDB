"""django-import-export resource classes for bibliography models."""

from __future__ import annotations

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from .models import Author, Reference, ReferenceKeyword


class AuthorResource(resources.ModelResource):
    """Export/import resource for Author."""

    class Meta:
        """Resource metadata."""

        model = Author
        fields = ("id", "last_name", "first_name")
        export_order = ("id", "last_name", "first_name")


class ReferenceResource(resources.ModelResource):
    """Export/import resource for Reference, with M2M widgets."""

    lead_author = fields.Field(
        column_name="lead_author",
        attribute="lead_author",
        widget=ForeignKeyWidget(Author, field="last_name"),
    )
    # ManyToManyWidget takes a model class (per django-import-export's actual
    # source); basedpyright's bundled third-party stub declares `model` bound
    # to `Model` (an instance), which is a stub bug, not a real type error.
    second_author = fields.Field(
        column_name="second_author",
        attribute="second_author",
        widget=ManyToManyWidget(Author, field="last_name", separator="; "),  # pyright: ignore[reportArgumentType]
    )
    supervisor = fields.Field(
        column_name="supervisor",
        attribute="supervisor",
        widget=ManyToManyWidget(Author, field="last_name", separator="; "),  # pyright: ignore[reportArgumentType]
    )
    keywords = fields.Field(
        column_name="keywords",
        attribute="keywords",
        widget=ManyToManyWidget(
            ReferenceKeyword,  # pyright: ignore[reportArgumentType]
            field="keyword",
            separator="; ",
        ),
    )

    class Meta:
        """Resource metadata."""

        model = Reference
        fields = (
            "id",
            "type",
            "year",
            "published",
            "lead_author",
            "second_author",
            "supervisor",
            "title",
            "journal",
            "volume",
            "number",
            "pages",
            "publisher",
            "location_of_publication",
            "doi",
            "issn",
            "isbn_print",
            "isbn_online",
            "abstract",
            "keywords",
            "how_to_cite",
        )
        export_order = (
            "id",
            "type",
            "year",
            "published",
            "lead_author",
            "second_author",
            "supervisor",
            "title",
            "journal",
            "volume",
            "number",
            "pages",
            "publisher",
            "location_of_publication",
            "doi",
            "issn",
            "isbn_print",
            "isbn_online",
            "abstract",
            "keywords",
            "how_to_cite",
        )
