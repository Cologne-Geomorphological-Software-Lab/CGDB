import './styles/dashboard.css';

import { map, wireCoordsDisplay } from './map/mapInstance.js';
import { fetchLocations, locationsLayer } from './layers/locations.js';
import { loadStudyAreas, studyAreasLayer } from './layers/studyAreas.js';
import { loadTransects, transectsLayer } from './layers/transects.js';
import { landformsTilesLayer } from './layers/landformsTiles.js';
import { wmsLayers } from './layers/wmsOverlays.js';
import { applyFilter, populateFilterDropdowns, wireFilterControls } from './ui/filters.js';
import { initEditControls } from './ui/editControls.js';
import { initLayersPanel, setLayerLoading } from './ui/layersPanel.js';
import { trackLoading } from './ui/loadingIndicator.js';
import { initMeasureControls } from './ui/measureControls.js';
import { wirePopupClose, wireClickHandler } from './ui/popup.js';
import { initSearch } from './ui/search.js';
import { wireSidebarTabs, wireSidebarToggle } from './ui/sidebar.js';
import { initToolbar } from './ui/toolbar.js';

const configEl = document.getElementById('cgdb-map-config');
const config = JSON.parse(configEl.textContent);
const { geojsonUrls, wmsProxyUrl, canEdit } = config;

map.addLayer(wmsLayers.bgr_geo);
map.addLayer(wmsLayers.macrostrat);
map.addLayer(landformsTilesLayer);
map.addLayer(studyAreasLayer);
map.addLayer(transectsLayer);
map.addLayer(locationsLayer);

wireCoordsDisplay();
wireSidebarTabs();
wireSidebarToggle(map);
wirePopupClose();
wireClickHandler(
  map,
  { locationsLayer, studyAreasLayer, transectsLayer, landformsLayer: landformsTilesLayer },
  wmsProxyUrl,
);

const { searchBtn, measureBtn, editBtn } = initToolbar(canEdit);
initSearch(searchBtn);
initMeasureControls(measureBtn);
if (editBtn) initEditControls(editBtn);

const layerMap = {
  locations: locationsLayer,
  study_areas: studyAreasLayer,
  transects: transectsLayer,
  landforms: landformsTilesLayer,
  bgr_geo: wmsLayers.bgr_geo,
  macrostrat: wmsLayers.macrostrat,
};
initLayersPanel(layerMap);

const trackedFetchLocations = trackLoading('locations', setLayerLoading, fetchLocations);
const trackedLoadStudyAreas = trackLoading('study_areas', setLayerLoading, loadStudyAreas);
const trackedLoadTransects = trackLoading('transects', setLayerLoading, loadTransects);

let allLocationFeatures = [];
trackedFetchLocations(geojsonUrls.locations).then((features) => {
  allLocationFeatures = features;
  applyFilter(allLocationFeatures);
  populateFilterDropdowns(allLocationFeatures);
});
wireFilterControls(() => applyFilter(allLocationFeatures));

trackedLoadStudyAreas(geojsonUrls.study_areas);
trackedLoadTransects(geojsonUrls.transects);
