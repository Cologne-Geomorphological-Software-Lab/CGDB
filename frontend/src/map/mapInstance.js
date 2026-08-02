import 'ol/ol.css';
import Map from 'ol/Map.js';
import View from 'ol/View.js';
import TileLayer from 'ol/layer/Tile.js';
import Overlay from 'ol/Overlay.js';
import Attribution from 'ol/control/Attribution.js';
import ScaleLine from 'ol/control/ScaleLine.js';
import Zoom from 'ol/control/Zoom.js';
import { fromLonLat, toLonLat } from 'ol/proj.js';

import { BASEMAPS } from './basemaps.js';

export const basemapLayer = new TileLayer({ source: BASEMAPS.esri_sat });

export const INITIAL_CENTER = fromLonLat([10, 30]);
export const INITIAL_ZOOM = 2;

const popupEl = document.getElementById('cgdb-popup');
export const popup = new Overlay({
  element: popupEl,
  positioning: 'bottom-center',
  offset: [0, -4],
  stopEvent: true,
  autoPan: { animation: { duration: 250 } },
});
export { popupEl };

export const shellEl = document.getElementById('cgdb-gis-shell');

export const map = new Map({
  target: 'cgdb-map',
  layers: [basemapLayer],
  view: new View({ center: INITIAL_CENTER, zoom: INITIAL_ZOOM }),
  // Fullscreen lives in ui/toolbar.js instead of OL's default-styled
  // FullScreen control, so every map tool shares one visual language.
  controls: [new Zoom(), new ScaleLine(), new Attribution({ collapsible: true })],
  overlays: [popup],
});

function resizeShell() {
  const top = shellEl.getBoundingClientRect().top + window.scrollY;
  shellEl.style.height = `${Math.max(400, window.innerHeight - top - 16)}px`;
}
window.addEventListener('resize', resizeShell);
resizeShell();
setTimeout(() => map.updateSize(), 50);

export function wireCoordsDisplay() {
  const coordsEl = document.getElementById('cgdb-coords');
  map.on('pointermove', (evt) => {
    if (evt.dragging) return;
    const ll = toLonLat(evt.coordinate);
    coordsEl.textContent = `${ll[1].toFixed(5)}° N   ${ll[0].toFixed(5)}° E`;
  });
}
