"""DRF router for geodata API endpoints — merged into prototype.api_router."""

from rest_framework.routers import DefaultRouter

from .api_views import LandformViewSet

router = DefaultRouter()
router.register(r"landforms", LandformViewSet, basename="landform")
