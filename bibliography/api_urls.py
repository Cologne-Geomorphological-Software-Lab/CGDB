"""DRF router for bibliography API endpoints — merged into prototype.api_router."""

from rest_framework.routers import DefaultRouter

from .api_views import AuthorViewSet, ReferenceKeywordViewSet, ReferenceViewSet

router = DefaultRouter()
router.register(r"authors", AuthorViewSet, basename="author")
router.register(
    r"reference-keywords", ReferenceKeywordViewSet, basename="referencekeyword"
)
router.register(r"references", ReferenceViewSet, basename="reference")
