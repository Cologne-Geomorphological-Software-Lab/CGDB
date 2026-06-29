"""GeoJSON serializers for geodata models."""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Landform

_LANDFORM_FIELDS = [
    "id",
    "murphy_code",
    "brid_nam",
    "name_str",
    "division",
    "province",
    "section",
    "continent",
    "structure",
    "moist_dry",
    "topog",
    "process",
    "glaciate",
    "volcanism",
    "volc_name",
    "si_vol_num",
    "vol_reg",
    "vol_prov",
    "plate_1",
    "plate_2",
    "plate_3",
    "plate_4",
    "plate_5",
    "notes",
    "area_geo",
    "shape_length",
    "shape_area",
    "source",
]


class LandformListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — geometry excluded."""

    class Meta:
        """Serializer metadata."""

        model = Landform
        fields = _LANDFORM_FIELDS


class LandformGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for detail view — includes full geometry."""

    class Meta:
        """Serializer metadata."""

        model = Landform
        geo_field = "geometry"
        fields = _LANDFORM_FIELDS
