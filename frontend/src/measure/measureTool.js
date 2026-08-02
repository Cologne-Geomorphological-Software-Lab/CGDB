import Draw from 'ol/interaction/Draw.js';
import DoubleClickZoom from 'ol/interaction/DoubleClickZoom.js';
import Overlay from 'ol/Overlay.js';
import VectorLayer from 'ol/layer/Vector.js';
import VectorSource from 'ol/source/Vector.js';
import Fill from 'ol/style/Fill.js';
import Stroke from 'ol/style/Stroke.js';
import Style from 'ol/style/Style.js';
import CircleStyle from 'ol/style/Circle.js';
import { getArea, getLength } from 'ol/sphere.js';
import { unByKey } from 'ol/Observable.js';

import { map } from '../map/mapInstance.js';

// Draw interactions finish a sketch on double-click — without disabling
// this default interaction while measuring, that same double-click also
// zooms the map, yanking the view away right as a measurement completes.
const doubleClickZoom = map
  .getInteractions()
  .getArray()
  .find((interaction) => interaction instanceof DoubleClickZoom);

// Re-enabling it must wait until the finishing dblclick's event cycle has
// fully finished: Map dispatches one browser event to every interaction in
// turn, and Polygon's finish (unlike LineString's) doesn't stop that
// propagation — re-enabling synchronously inside the `drawend` handler left
// DoubleClickZoom active again in time to also see that same event and zoom
// the map right as the measurement completed.
function reenableDoubleClickZoomNextTick() {
  setTimeout(() => doubleClickZoom?.setActive(true), 0);
}

// A dedicated source/layer — measurement sketches must never mix into a
// data layer's own source (locations/study areas/etc.).
const measureSource = new VectorSource();
const measureLayer = new VectorLayer({
  source: measureSource,
  style: new Style({
    fill: new Fill({ color: 'rgba(249,115,22,0.15)' }),
    stroke: new Stroke({ color: '#f97316', width: 2, lineDash: [8, 6] }),
    image: new CircleStyle({
      radius: 5,
      fill: new Fill({ color: '#f97316' }),
    }),
  }),
  zIndex: 20,
});
map.addLayer(measureLayer);

let activeDraw = null;
let activeSketchListenerKey = null;
let activeTooltipEl = null;
let activeTooltipOverlay = null;
const committedTooltipOverlays = [];

function formatLength(geometry) {
  const length = getLength(geometry, { projection: map.getView().getProjection() });
  return length > 1000 ? `${(length / 1000).toFixed(2)} km` : `${length.toFixed(1)} m`;
}

function formatArea(geometry) {
  const area = getArea(geometry, { projection: map.getView().getProjection() });
  return area > 1e6 ? `${(area / 1e6).toFixed(2)} km²` : `${area.toFixed(1)} m²`;
}

function tooltipPosition(type, geometry) {
  return type === 'Polygon' ? geometry.getInteriorPoint().getCoordinates() : geometry.getLastCoordinate();
}

// Cancels whatever measurement is currently mid-draw (an unfinished sketch
// has no useful result yet, so its tooltip is discarded, not committed).
function cancelActiveDraw() {
  doubleClickZoom?.setActive(true);
  if (activeSketchListenerKey) {
    unByKey(activeSketchListenerKey);
    activeSketchListenerKey = null;
  }
  if (activeDraw) {
    map.removeInteraction(activeDraw);
    activeDraw = null;
  }
  if (activeTooltipOverlay) {
    map.removeOverlay(activeTooltipOverlay);
    activeTooltipOverlay = null;
    activeTooltipEl = null;
  }
}

export function startMeasure(type) {
  cancelActiveDraw();
  doubleClickZoom?.setActive(false);

  activeTooltipEl = document.createElement('div');
  activeTooltipEl.className = 'measure-tooltip measure-tooltip-active';
  activeTooltipOverlay = new Overlay({
    element: activeTooltipEl,
    offset: [0, -8],
    positioning: 'bottom-center',
    stopEvent: false,
  });
  map.addOverlay(activeTooltipOverlay);

  activeDraw = new Draw({ source: measureSource, type });
  map.addInteraction(activeDraw);

  activeDraw.on('drawstart', (evt) => {
    activeSketchListenerKey = evt.feature.getGeometry().on('change', (changeEvt) => {
      const geometry = changeEvt.target;
      activeTooltipEl.textContent = type === 'Polygon' ? formatArea(geometry) : formatLength(geometry);
      activeTooltipOverlay.setPosition(tooltipPosition(type, geometry));
    });
  });

  activeDraw.on('drawend', (evt) => {
    reenableDoubleClickZoomNextTick();
    if (activeSketchListenerKey) {
      unByKey(activeSketchListenerKey);
      activeSketchListenerKey = null;
    }
    activeTooltipEl.className = 'measure-tooltip measure-tooltip-done';
    activeTooltipOverlay.setPosition(tooltipPosition(type, evt.feature.getGeometry()));
    committedTooltipOverlays.push(activeTooltipOverlay);
    activeTooltipOverlay = null;
    activeTooltipEl = null;
    map.removeInteraction(activeDraw);
    activeDraw = null;
  });
}

export function clearMeasure() {
  cancelActiveDraw();
  measureSource.clear();
  committedTooltipOverlays.forEach((overlay) => map.removeOverlay(overlay));
  committedTooltipOverlays.length = 0;
}
