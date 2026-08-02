"""DRF serializers for the prototype app."""

from rest_framework import serializers

from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    """Minimal Project serializer — used to populate project pickers.

    Currently only consumed by the map dashboard's "new StudyArea/Transect"
    creation form (frontend/src/edit/), which needs a project to attach a
    new record to.
    """

    class Meta:
        """Serializer metadata."""

        model = Project
        fields = ["id", "title", "label"]
