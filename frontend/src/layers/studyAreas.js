import VectorLayer from 'ol/layer/Vector.js';
import VectorSource from 'ol/source/Vector.js';

import { readFeatureCollection } from '../utils/geojsonFormat.js';
import { studyAreaStyle } from '../styles/mapStyles.js';

export const studyAreaSource = new VectorSource();

export const studyAreasLayer = new VectorLayer({
  source: studyAreaSource,
  style: studyAreaStyle,
  zIndex: 5,
});

export async function loadStudyAreas(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to load study areas (HTTP ${resp.status})`);
  const data = await resp.json();
  studyAreaSource.addFeatures(readFeatureCollection(data));
}
