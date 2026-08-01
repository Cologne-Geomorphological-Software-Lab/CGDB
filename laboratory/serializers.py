"""DRF serializers for laboratory models."""

from rest_framework import serializers

from .models import (
    Accessory,
    AccessoryParameter,
    Calibration,
    Device,
    Firmware,
    Manufacturer,
    Method,
)


class ManufacturerSerializer(serializers.ModelSerializer):
    """Serializer for Manufacturer records."""

    class Meta:
        """Serializer metadata."""

        model = Manufacturer
        fields = ["id", "name", "website"]


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device records."""

    class Meta:
        """Serializer metadata."""

        model = Device
        fields = ["id", "name", "description", "token", "manufacturer"]


class AccessorySerializer(serializers.ModelSerializer):
    """Serializer for Accessory records."""

    class Meta:
        """Serializer metadata."""

        model = Accessory
        fields = ["id", "device", "name", "description"]


class AccessoryParameterSerializer(serializers.ModelSerializer):
    """Serializer for AccessoryParameter records."""

    class Meta:
        """Serializer metadata."""

        model = AccessoryParameter
        fields = [
            "id",
            "method",
            "accessory",
            "parameter_name",
            "parameter_value",
            "parameter_unit",
        ]


class MethodSerializer(serializers.ModelSerializer):
    """Serializer for Method records."""

    class Meta:
        """Serializer metadata."""

        model = Method
        fields = [
            "id",
            "name",
            "description",
            "token",
            "device",
            "category",
            "laboratory",
            "available",
        ]


class CalibrationSerializer(serializers.ModelSerializer):
    """Serializer for Calibration records."""

    class Meta:
        """Serializer metadata."""

        model = Calibration
        fields = [
            "id",
            "device",
            "date",
            "researcher",
            "remarks",
            "created_at",
            "modified_at",
        ]


class FirmwareSerializer(serializers.ModelSerializer):
    """Serializer for Firmware records."""

    class Meta:
        """Serializer metadata."""

        model = Firmware
        fields = [
            "id",
            "device",
            "version",
            "installation_date",
            "changelog",
        ]
