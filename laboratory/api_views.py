"""REST API ViewSets for laboratory models.

The laboratory app is a shared equipment/method catalog, not project-scoped
data — every viewset here is IsAuthenticated-only, matching how field_data's
lookup-table viewsets (ExposureTypeViewSet, SampleTypeViewSet) skip project
scoping entirely.
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import (
    Accessory,
    AccessoryParameter,
    Calibration,
    Device,
    Firmware,
    Manufacturer,
    Method,
)
from .serializers import (
    AccessoryParameterSerializer,
    AccessorySerializer,
    CalibrationSerializer,
    DeviceSerializer,
    FirmwareSerializer,
    ManufacturerSerializer,
    MethodSerializer,
)


class ManufacturerViewSet(ReadOnlyModelViewSet):
    """Read-only list of equipment manufacturers."""

    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class DeviceViewSet(ReadOnlyModelViewSet):
    """Read-only list of laboratory devices."""

    queryset = Device.objects.select_related("manufacturer")
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["manufacturer"]
    search_fields = ["name", "description", "token"]
    ordering_fields = ["name", "manufacturer"]
    ordering = ["name"]


class AccessoryViewSet(ReadOnlyModelViewSet):
    """Read-only list of device accessories."""

    queryset = Accessory.objects.select_related("device")
    serializer_class = AccessorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["device"]
    search_fields = ["name", "description"]
    ordering_fields = ["device", "name"]
    ordering = ["device", "name"]


class AccessoryParameterViewSet(ReadOnlyModelViewSet):
    """Read-only list of accessory parameter values."""

    queryset = AccessoryParameter.objects.select_related("accessory")
    serializer_class = AccessoryParameterSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["accessory", "method"]
    search_fields = ["parameter_name"]
    ordering_fields = ["accessory", "parameter_name"]
    ordering = ["accessory", "parameter_name"]


class MethodViewSet(ReadOnlyModelViewSet):
    """Read-only list of laboratory analytical methods."""

    queryset = Method.objects.select_related("device")
    serializer_class = MethodSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["category", "laboratory", "available", "device"]
    search_fields = ["name", "description", "token"]
    ordering_fields = ["name", "category", "laboratory"]
    ordering = ["name"]


class CalibrationViewSet(ReadOnlyModelViewSet):
    """Read-only list of device calibration events."""

    queryset = Calibration.objects.select_related("device", "researcher")
    serializer_class = CalibrationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["device", "researcher"]
    ordering_fields = ["date"]
    ordering = ["-date"]


class FirmwareViewSet(ReadOnlyModelViewSet):
    """Read-only list of device firmware versions."""

    queryset = Firmware.objects.select_related("device")
    serializer_class = FirmwareSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["device"]
    ordering_fields = ["installation_date"]
    ordering = ["-installation_date"]
