"""DRF router for laboratory API endpoints — merged into prototype.api_router."""

from rest_framework.routers import DefaultRouter

from .api_views import (
    AccessoryParameterViewSet,
    AccessoryViewSet,
    CalibrationViewSet,
    DeviceViewSet,
    FirmwareViewSet,
    ManufacturerViewSet,
    MethodViewSet,
)

router = DefaultRouter()
router.register(r"manufacturers", ManufacturerViewSet, basename="manufacturer")
router.register(r"devices", DeviceViewSet, basename="device")
router.register(r"accessories", AccessoryViewSet, basename="accessory")
router.register(
    r"accessory-parameters",
    AccessoryParameterViewSet,
    basename="accessoryparameter",
)
router.register(r"methods", MethodViewSet, basename="method")
router.register(r"calibrations", CalibrationViewSet, basename="calibration")
router.register(r"firmwares", FirmwareViewSet, basename="firmware")
