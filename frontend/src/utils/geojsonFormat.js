import GeoJSON from 'ol/format/GeoJSON.js';

// Single shared projection boundary: the API always sends WGS84 (EPSG:4326),
// the map view always renders in Web Mercator (EPSG:3857). Every layer that
// reads GeoJSON from the API must use this instance rather than constructing
// its own — fixing the SRID/projection conversion once, in one place.
export const geojsonFormat = new GeoJSON({
  dataProjection: 'EPSG:4326',
  featureProjection: 'EPSG:3857',
});

// tech debt FE3: API JSON used to be fed straight into readFeatures() with
// no shape check. A backend contract change (a renamed field, or an error
// payload — e.g. DRF's {"detail": "..."} — returned instead of GeoJSON on a
// 403/404) then failed deep inside OL's parser instead of with a clear
// message at the loader. Every layer loader should call this instead of
// geojsonFormat.readFeatures() directly.
export function readFeatureCollection(data) {
  if (!data || data.type !== 'FeatureCollection' || !Array.isArray(data.features)) {
    throw new Error('Expected a GeoJSON FeatureCollection, got something else.');
  }
  return geojsonFormat.readFeatures(data);
}
