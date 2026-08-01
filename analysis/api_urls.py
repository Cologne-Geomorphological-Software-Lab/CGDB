"""DRF router for analysis API endpoints — merged into prototype.api_router."""

from rest_framework.routers import DefaultRouter

from .api_views import (
    AlgorithmViewSet,
    CosmogenicNuclideDatingViewSet,
    CountingViewSet,
    GenericMeasurementViewSet,
    GrainSizeViewSet,
    LuminescenceDatingViewSet,
    MeasurementSeriesViewSet,
    MicroXRFElementMapViewSet,
    MicroXRFMeasurementViewSet,
    ParameterViewSet,
    PollenCountViewSet,
    PollenViewSet,
    RadiocarbonDatingViewSet,
    RawMeasurementViewSet,
    RawProcessingViewSet,
)

router = DefaultRouter()
router.register(r"algorithms", AlgorithmViewSet, basename="algorithm")
router.register(
    r"raw-measurements", RawMeasurementViewSet, basename="rawmeasurement"
)
router.register(
    r"raw-processing", RawProcessingViewSet, basename="rawprocessing"
)
router.register(r"countings", CountingViewSet, basename="counting")
router.register(r"pollen", PollenViewSet, basename="pollen")
router.register(r"pollen-counts", PollenCountViewSet, basename="pollencount")
router.register(
    r"luminescence-datings",
    LuminescenceDatingViewSet,
    basename="luminescencedating",
)
router.register(
    r"radiocarbon-datings",
    RadiocarbonDatingViewSet,
    basename="radiocarbondating",
)
router.register(
    r"cosmogenic-nuclide-datings",
    CosmogenicNuclideDatingViewSet,
    basename="cosmogenicnuclidedating",
)
router.register(r"parameters", ParameterViewSet, basename="parameter")
router.register(
    r"measurement-series",
    MeasurementSeriesViewSet,
    basename="measurementseries",
)
router.register(
    r"generic-measurements",
    GenericMeasurementViewSet,
    basename="genericmeasurement",
)
router.register(r"grain-sizes", GrainSizeViewSet, basename="grainsize")
router.register(
    r"microxrf-measurements",
    MicroXRFMeasurementViewSet,
    basename="microxrfmeasurement",
)
router.register(
    r"microxrf-element-maps",
    MicroXRFElementMapViewSet,
    basename="microxrfelementmap",
)
