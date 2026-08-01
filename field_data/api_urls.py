"""DRF router for field_data API endpoints — merged into prototype.api_router."""

from rest_framework.routers import DefaultRouter

from .api_views import (
    CampaignViewSet,
    ExposureTypeViewSet,
    LayerViewSet,
    LocationViewSet,
    SampleTypeViewSet,
    SampleViewSet,
    StudyAreaViewSet,
    TransectViewSet,
)

router = DefaultRouter()
router.register(r"locations", LocationViewSet, basename="location")
router.register(r"samples", SampleViewSet, basename="sample")
router.register(r"campaigns", CampaignViewSet, basename="campaign")
router.register(r"study-areas", StudyAreaViewSet, basename="studyarea")
router.register(r"layers", LayerViewSet, basename="layer")
router.register(r"transects", TransectViewSet, basename="transect")
router.register(
    r"exposure-types", ExposureTypeViewSet, basename="exposuretype"
)
router.register(r"sample-types", SampleTypeViewSet, basename="sampletype")
