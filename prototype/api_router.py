"""Central DRF router for all CGDB API endpoints."""

from rest_framework.routers import DefaultRouter

from field_data.api_views import (
    CampaignViewSet,
    ExposureTypeViewSet,
    LayerViewSet,
    LocationViewSet,
    SampleTypeViewSet,
    SampleViewSet,
    StudyAreaViewSet,
    TransectViewSet,
)
from geodata.api_views import (
    GeomorphonViewSet,
    LandformViewSet,
    WorldCoverViewSet,
)

router = DefaultRouter()

# Geodata layers
router.register(r"geomorphons", GeomorphonViewSet, basename="geomorphon")
router.register(r"landforms", LandformViewSet, basename="landform")
router.register(r"worldcover", WorldCoverViewSet, basename="worldcover")

# field_data
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
