import Cluster from 'ol/source/Cluster.js';
import VectorLayer from 'ol/layer/Vector.js';
import VectorSource from 'ol/source/Vector.js';

import { geojsonFormat } from '../utils/geojsonFormat.js';
import { clusterStyle, makePointStyle } from '../styles/mapStyles.js';

export const locationSource = new VectorSource();
const clusterSource = new Cluster({ source: locationSource, distance: 40 });

export const locationsLayer = new VectorLayer({
  source: clusterSource,
  style: (feature) => {
    const inner = feature.get('features');
    if (!inner || !inner.length) return null;
    if (inner.length > 1) return clusterStyle(inner.length);
    return makePointStyle(inner[0].get('location_type'), inner[0].get('data_source'));
  },
  zIndex: 10,
});

// All fetched location features, unfiltered — the source of truth for
// ui/filters.js's client-side filtering.
export async function fetchLocations(url) {
  const resp = await fetch(url);
  const data = await resp.json();
  return geojsonFormat.readFeatures(data);
}

export function setVisibleLocations(features) {
  locationSource.clear();
  locationSource.addFeatures(features);
}
