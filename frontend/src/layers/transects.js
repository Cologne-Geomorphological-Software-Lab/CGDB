import VectorLayer from 'ol/layer/Vector.js';
import VectorSource from 'ol/source/Vector.js';

import { readFeatureCollection } from '../utils/geojsonFormat.js';
import { transectStyle } from '../styles/mapStyles.js';

export const transectSource = new VectorSource();

export const transectsLayer = new VectorLayer({
  source: transectSource,
  style: transectStyle,
  zIndex: 6,
});

export async function loadTransects(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to load transects (HTTP ${resp.status})`);
  const data = await resp.json();
  transectSource.addFeatures(readFeatureCollection(data));
}
