"""Django-filter FilterSet definitions for Location and Sample list views."""

import django_filters as filters

from .models import Location, Sample


class LocationFilter(filters.FilterSet):
    """Filter for the Location changelist."""

    class Meta:
        """FilterSet metadata."""

        model = Location
        fields = [
            "exposure_type",
            "identifier",
            "liner",
            "sampling",
            "study_site__study_area",
            "study_site",
            "tags",
            "date_of_record",
            "processor",
            "transect",
        ]


LocationFilter.base_filters["study_site__study_area"].label = "Study area"


class SampleFilter(filters.FilterSet):
    """Filter for the Sample changelist."""

    class Meta:
        """FilterSet metadata."""

        model = Sample
        fields = [
            "processor",
            "type",
            "tags",
            "depth_mid",
            "layer",
        ]
