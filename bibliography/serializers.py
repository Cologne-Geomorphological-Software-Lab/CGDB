"""DRF serializers for bibliography models."""

from rest_framework import serializers

from .models import Author, Reference, ReferenceKeyword


class AuthorSerializer(serializers.ModelSerializer):
    """Serializer for Author records."""

    class Meta:
        """Serializer metadata."""

        model = Author
        fields = ["id", "last_name", "first_name", "user"]


class ReferenceKeywordSerializer(serializers.ModelSerializer):
    """Serializer for ReferenceKeyword records."""

    class Meta:
        """Serializer metadata."""

        model = ReferenceKeyword
        fields = ["id", "keyword", "keyword_ger"]


class ReferenceSerializer(serializers.ModelSerializer):
    """Serializer for Reference records.

    Reference.project is an optional ManyToManyField — Reference is treated
    as a shared literature catalog (visible to all authenticated users,
    like data_source="literature" elsewhere), not project-scoped, so
    project appears here as a plain read-only relation list.
    """

    class Meta:
        """Serializer metadata."""

        model = Reference
        fields = [
            "id",
            "title",
            "year",
            "published",
            "parent_publication",
            "lead_author",
            "second_author",
            "supervisor",
            "abstract",
            "journal",
            "volume",
            "number",
            "pages",
            "publisher",
            "location_of_publication",
            "type",
            "project",
            "doi",
            "issn",
            "isbn_print",
            "isbn_online",
            "how_to_cite",
            "keywords",
            "created_at",
            "modified_at",
        ]
