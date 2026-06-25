"""GeoJSON serializers for geodata models."""

from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Geomorphon, Landform, WorldCover


class GeomorphonGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for Geomorphon terrain form polygons."""

    class Meta:
        """Serializer metadata."""

        model = Geomorphon
        geo_field = "geometry"
        fields = [
            "id",
            "geomorphon_class",
            "source",
            "resolution_m",
            "study_area",
            "created_at",
        ]


class LandformGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for Murphy Landform region polygons."""

    class Meta:
        """Serializer metadata."""

        model = Landform
        geo_field = "geometry"
        fields = [
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


class WorldCoverGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for ESA WorldCover land cover polygons."""

    class Meta:
        """Serializer metadata."""

        model = WorldCover
        geo_field = "geometry"
        fields = [
            "id",
            "landcover_class",
            "year",
            "source",
            "created_at",
        ]
