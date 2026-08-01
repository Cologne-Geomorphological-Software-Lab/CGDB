"""Central DRF router — aggregates each app's own router."""

from rest_framework.routers import DefaultRouter

from analysis.api_urls import router as analysis_router
from bibliography.api_urls import router as bibliography_router
from field_data.api_urls import router as field_data_router
from geodata.api_urls import router as geodata_router
from laboratory.api_urls import router as laboratory_router
from raster_data.api_urls import router as raster_data_router

router = DefaultRouter()
router.registry.extend(field_data_router.registry)
router.registry.extend(geodata_router.registry)
router.registry.extend(raster_data_router.registry)
router.registry.extend(laboratory_router.registry)
router.registry.extend(bibliography_router.registry)
router.registry.extend(analysis_router.registry)
