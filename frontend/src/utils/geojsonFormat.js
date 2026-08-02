import GeoJSON from 'ol/format/GeoJSON.js';

// Single shared projection boundary: the API always sends WGS84 (EPSG:4326),
// the map view always renders in Web Mercator (EPSG:3857). Every layer that
// reads GeoJSON from the API must use this instance rather than constructing
// its own — fixing the SRID/projection conversion once, in one place.
export const geojsonFormat = new GeoJSON({
  dataProjection: 'EPSG:4326',
  featureProjection: 'EPSG:3857',
});
