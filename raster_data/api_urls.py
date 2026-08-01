"""DRF router for raster_data API endpoints — merged into prototype.api_router."""

from rest_framework.routers import DefaultRouter

from .api_views import (
    DataSourceViewSet,
    RasterDatasetViewSet,
    RasterSceneViewSet,
)

router = DefaultRouter()
router.register(r"data-sources", DataSourceViewSet, basename="datasource")
router.register(r"raster-scenes", RasterSceneViewSet, basename="rasterscene")
router.register(
    r"raster-datasets", RasterDatasetViewSet, basename="rasterdataset"
)
