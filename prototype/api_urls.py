"""DRF router for the prototype app's API endpoints — merged into prototype.api_router."""

from rest_framework.routers import DefaultRouter

from .api_views import ProjectViewSet

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
