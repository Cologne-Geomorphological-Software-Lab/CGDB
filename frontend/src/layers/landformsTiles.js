import VectorTileLayer from 'ol/layer/VectorTile.js';
import VectorTileSource from 'ol/source/VectorTile.js';
import MVT from 'ol/format/MVT.js';

import { landformStyle } from '../styles/mapStyles.js';

// Replaces the old GeoJSON `?bbox=` viewport-fetch approach for the
// dashboard's own rendering: OpenLayers' VectorTileLayer already handles
// viewport-driven tile loading and zoom gating natively, so none of the old
// layers/landforms.js module's manual moveend/AbortController/zoom-threshold
// bookkeeping is needed here. Tiles are Web Mercator by convention, so no
// dataProjection/featureProjection config is needed on the MVT format
// either. The GeoJSON endpoint itself is untouched — Morphogrid (an
// external consumer) still depends on it.
const landformsTileSource = new VectorTileSource({
  format: new MVT(),
  url: '/api/v1/landforms/tiles/{z}/{x}/{y}.mvt',
});

export const landformsTilesLayer = new VectorTileLayer({
  source: landformsTileSource,
  style: landformStyle,
  visible: false,
  opacity: 0.7,
  // Matches the old GeoJSON path's MIN_LANDFORM_ZOOM=4 gating — below this
  // the global dataset isn't worth rendering.
  minZoom: 3,
  zIndex: 1,
});
