import ImageLayer from 'ol/layer/Image.js';
import ImageWMS from 'ol/source/ImageWMS.js';
import TileLayer from 'ol/layer/Tile.js';
import XYZ from 'ol/source/XYZ.js';

import { esc } from '../utils/esc.js';

export const wmsLayers = {
  bgr_geo: new ImageLayer({
    visible: false,
    opacity: 0.7,
    source: new ImageWMS({
      url: 'https://services.bgr.de/wms/grundwasser/huek250/',
      params: { LAYERS: '0,1,2,3,4,5,6,7', FORMAT: 'image/png', TRANSPARENT: 'true' },
      ratio: 1,
      crossOrigin: null,
      attributions: '&copy; BGR',
    }),
  }),
  macrostrat: new TileLayer({
    visible: false,
    opacity: 0.8,
    source: new XYZ({
      url: 'https://tiles.macrostrat.org/carto/{z}/{x}/{y}.png',
      maxZoom: 16,
      attributions: '&copy; <a href="https://macrostrat.org">Macrostrat</a>',
    }),
    zIndex: 3,
  }),
};

// Macrostrat is a plain XYZ tile layer, not WMS — it has no GetFeatureInfo.
const WMS_INFO_ORDER = ['bgr_geo'];

function rowsFromGml(xmlText) {
  const doc = new DOMParser().parseFromString(xmlText, 'text/xml');
  let rows = '';
  doc.querySelectorAll('*').forEach((el) => {
    if (el.children.length === 0 && el.textContent.trim() && el.localName.indexOf(':') === -1) {
      rows += `<tr><td>${esc(el.localName)}</td><td>${esc(el.textContent.trim())}</td></tr>`;
    }
  });
  return rows;
}

// Try each visible WMS overlay's GetFeatureInfo in order, via the server-side
// proxy (avoids browser CORS restrictions). Resolves to an HTML fragment for
// the popup, or null if nothing responded with usable info.
export async function fetchFeatureInfoHtml(map, coordinate, wmsProxyUrl) {
  const view = map.getView();
  const resolution = view.getResolution();
  const projection = view.getProjection();

  for (const key of WMS_INFO_ORDER) {
    const layer = wmsLayers[key];
    if (!layer.getVisible()) continue;
    const url = layer.getSource().getFeatureInfoUrl(coordinate, resolution, projection, {
      INFO_FORMAT: 'application/vnd.ogc.gml',
      FEATURE_COUNT: 5,
    });
    if (!url) continue;
    try {
      const resp = await fetch(`${wmsProxyUrl}?url=${encodeURIComponent(url)}`);
      const text = await resp.text();
      const rows = rowsFromGml(text);
      if (rows) return `<table class="wms-info-table"><tbody>${rows}</tbody></table>`;
    } catch {
      // try the next overlay
    }
  }
  return null;
}
