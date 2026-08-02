import VectorLayer from 'ol/layer/Vector.js';
import VectorSource from 'ol/source/Vector.js';

import { geojsonFormat } from '../utils/geojsonFormat.js';
import { transectStyle } from '../styles/mapStyles.js';

export const transectSource = new VectorSource();

export const transectsLayer = new VectorLayer({
  source: transectSource,
  style: transectStyle,
  zIndex: 6,
});

export async function loadTransects(url) {
  const resp = await fetch(url);
  const data = await resp.json();
  transectSource.addFeatures(geojsonFormat.readFeatures(data));
}
