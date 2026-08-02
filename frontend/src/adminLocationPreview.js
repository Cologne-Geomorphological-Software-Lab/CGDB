import 'ol/ol.css';
import Map from 'ol/Map.js';
import View from 'ol/View.js';
import TileLayer from 'ol/layer/Tile.js';
import VectorLayer from 'ol/layer/Vector.js';
import VectorSource from 'ol/source/Vector.js';
import XYZ from 'ol/source/XYZ.js';
import Feature from 'ol/Feature.js';
import Point from 'ol/geom/Point.js';
import Circle from 'ol/style/Circle.js';
import Fill from 'ol/style/Fill.js';
import Stroke from 'ol/style/Stroke.js';
import Style from 'ol/style/Style.js';
import ScaleLine from 'ol/control/ScaleLine.js';
import { fromLonLat } from 'ol/proj.js';
import proj4 from 'proj4';

// Standalone entry point for field_data/admin.py's LocationAdmin.map_preview —
// a small satellite preview embedded in the Location change form, separate
// from the map dashboard's main.js bundle (different page, different Django
// admin context). Replaces the old CDN-loaded OL 10 + proj4js UMD globals;
// this module self-initializes on load instead of waiting to be called.

function utmProj4(srid) {
  if (srid >= 32601 && srid <= 32660) {
    return `+proj=utm +zone=${srid - 32600} +datum=WGS84 +units=m +no_defs`;
  }
  if (srid >= 32701 && srid <= 32760) {
    return `+proj=utm +zone=${srid - 32700} +south +datum=WGS84 +units=m +no_defs`;
  }
  return null;
}

function toWGS84(easting, northing, srid) {
  if (srid === 4326) return [easting, northing];
  const def = utmProj4(srid);
  return def ? proj4(def, 'WGS84', [easting, northing]) : null;
}

function initPreview(container) {
  const lon = Number(container.dataset.lon);
  const lat = Number(container.dataset.lat);

  const markerSource = new VectorSource({
    features: [new Feature({ geometry: new Point(fromLonLat([lon, lat])) })],
  });

  const map = new Map({
    target: container,
    layers: [
      new TileLayer({
        source: new XYZ({
          url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          maxZoom: 17,
          attributions: 'Tiles &copy; Esri',
        }),
      }),
      new VectorLayer({
        source: markerSource,
        style: new Style({
          image: new Circle({
            radius: 8,
            fill: new Fill({ color: '#3b82f6' }),
            stroke: new Stroke({ color: '#1d4ed8', width: 2 }),
          }),
        }),
      }),
    ],
    view: new View({ center: fromLonLat([lon, lat]), zoom: 14 }),
    controls: [new ScaleLine()],
  });

  function updateMarker() {
    const easting = Number.parseFloat(document.getElementById('id_easting')?.value);
    const northing = Number.parseFloat(document.getElementById('id_northing')?.value);
    const srid = Number.parseInt(document.getElementById('id_srid')?.value, 10) || 4326;
    if (Number.isNaN(easting) || Number.isNaN(northing)) return;
    const wgs84 = toWGS84(easting, northing, srid);
    if (!wgs84) return;
    const coord = fromLonLat(wgs84);
    markerSource.getFeatures()[0].getGeometry().setCoordinates(coord);
    map.getView().setCenter(coord);
  }

  ['id_easting', 'id_northing', 'id_srid'].forEach((id) => {
    document.getElementById(id)?.addEventListener('change', updateMarker);
  });
}

document.querySelectorAll('.cgdb-loc-preview').forEach(initPreview);
