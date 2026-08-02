import Circle from 'ol/style/Circle.js';
import Fill from 'ol/style/Fill.js';
import RegularShape from 'ol/style/RegularShape.js';
import Stroke from 'ol/style/Stroke.js';
import Style from 'ol/style/Style.js';
import Text from 'ol/style/Text.js';

import {
  CLUSTER_LEGEND,
  LANDFORM_CONTINENT_LEGEND,
  LANDFORM_DEFAULT_STROKE,
  LITERATURE_LEGEND,
  STUDY_AREA_LEGEND,
  TRANSECT_LEGEND,
  resolveLocationTypeEntry,
} from './legendContent.js';

function shapeImage(shape, { fill, stroke, radius = 7 }) {
  if (shape === 'circle') return new Circle({ radius, fill, stroke });
  if (shape === 'square') {
    return new RegularShape({ points: 4, radius, angle: Math.PI / 4, fill, stroke });
  }
  if (shape === 'diamond') {
    return new RegularShape({ points: 4, radius: radius + 1, angle: 0, fill, stroke });
  }
  return new RegularShape({ points: 3, radius: radius + 1, fill, stroke });
}

export function makePointStyle(locType, dataSource) {
  const isLiterature = dataSource === 'literature';
  const entry = isLiterature ? LITERATURE_LEGEND : resolveLocationTypeEntry(locType);
  const fill = new Fill({ color: entry.fill });
  const stroke = new Stroke({ color: entry.stroke, width: 1.5 });
  const shape = isLiterature ? 'circle' : entry.shape;
  const image = shapeImage(shape, { fill, stroke, radius: isLiterature ? 5 : 7 });
  return new Style({ image });
}

export function clusterStyle(count) {
  const r = Math.min(8 + Math.log(count + 1) * 3, 22);
  return new Style({
    image: new Circle({
      radius: r,
      fill: new Fill({ color: CLUSTER_LEGEND.fill }),
      stroke: new Stroke({ color: CLUSTER_LEGEND.stroke, width: 1.5 }),
    }),
    text: new Text({
      text: String(count),
      fill: new Fill({ color: '#fff' }),
      font: 'bold 11px sans-serif',
    }),
  });
}

const LANDFORM_CONTINENT_STROKE = Object.fromEntries(
  LANDFORM_CONTINENT_LEGEND.map((entry) => [entry.label, entry.stroke]),
);

export function landformStyle(feature) {
  const continent = feature.get('continent') || '';
  let stroke = LANDFORM_DEFAULT_STROKE;
  for (const [label, color] of Object.entries(LANDFORM_CONTINENT_STROKE)) {
    if (continent.indexOf(label) !== -1) {
      stroke = color;
      break;
    }
  }
  return new Style({
    fill: new Fill({ color: 'rgba(0,0,0,0)' }),
    stroke: new Stroke({ color: stroke, width: 1.2 }),
  });
}

// Amber, distinct from every layer's own saved color (StudyArea's green,
// Transect's orange) — an edit that hasn't been confirmed saved yet always
// reads the same way regardless of which layer it's on.
const PENDING_COLOR = '#d97706';

export function studyAreaStyle(feature) {
  const pending = feature.get('cgdbPending');
  return new Style({
    fill: new Fill({
      color: pending ? 'rgba(217,119,6,0.15)' : STUDY_AREA_LEGEND.fill,
    }),
    stroke: new Stroke({
      color: pending ? PENDING_COLOR : STUDY_AREA_LEGEND.stroke,
      width: 1.5,
      lineDash: pending ? [4, 4] : undefined,
    }),
  });
}

export function transectStyle(feature) {
  const pending = feature.get('cgdbPending');
  return new Style({
    stroke: new Stroke({
      color: pending ? PENDING_COLOR : TRANSECT_LEGEND.stroke,
      width: 2,
      lineDash: [6, 4],
    }),
  });
}
