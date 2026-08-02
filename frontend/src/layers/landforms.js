import VectorLayer from 'ol/layer/Vector.js';
import VectorSource from 'ol/source/Vector.js';
import { transformExtent } from 'ol/proj.js';

import { map } from '../map/mapInstance.js';
import { debounce } from '../utils/debounce.js';
import { geojsonFormat } from '../utils/geojsonFormat.js';
import { landformStyle } from '../styles/mapStyles.js';

export const landformSource = new VectorSource();

export const landformsLayer = new VectorLayer({
  source: landformSource,
  style: landformStyle,
  visible: false,
  opacity: 0.7,
  zIndex: 1,
});

const MIN_LANDFORM_ZOOM = 4;
let abortController = null;

export function reloadLandforms(baseUrl) {
  if (!landformsLayer.getVisible()) return;
  const view = map.getView();
  const zoom = view.getZoom() || 0;
  if (zoom < MIN_LANDFORM_ZOOM) {
    landformSource.clear();
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    return;
  }
  const size = map.getSize();
  if (!size) return;
  const extent = view.calculateExtent(size);
  const ll = transformExtent(extent, view.getProjection(), 'EPSG:4326');
  const minx = Math.max(ll[0], -180);
  const miny = Math.max(ll[1], -90);
  const maxx = Math.min(ll[2], 180);
  const maxy = Math.min(ll[3], 90);
  if (maxx <= minx || maxy <= miny) return;

  const bbox = [minx, miny, maxx, maxy].map((v) => v.toFixed(6)).join(',');
  const url = `${baseUrl}?bbox=${bbox}`;

  if (abortController) abortController.abort();
  abortController = new AbortController();

  fetch(url, { signal: abortController.signal })
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((data) => {
      landformSource.clear();
      landformSource.addFeatures(geojsonFormat.readFeatures(data));
      abortController = null;
    })
    .catch((err) => {
      if (err.name !== 'AbortError') console.error('reloadLandforms failed:', err);
    });
}

export function wireLandformsReload(baseUrl) {
  map.on('moveend', debounce(() => reloadLandforms(baseUrl), 300));
}

export function clearLandforms() {
  landformSource.clear();
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
}
