import { basemapLayer } from '../map/mapInstance.js';
import { BASEMAPS } from '../map/basemaps.js';
import { clearLandforms, reloadLandforms } from '../layers/landforms.js';

const LEGEND_IDS = {
  bgr_geo: 'legend-bgr',
  macrostrat: 'legend-macrostrat',
  landforms: 'legend-landforms',
};

// Wires the sidebar's layer checkboxes/opacity sliders/basemap radios to the
// map's layers, and shows/hides the matching legend panel per checkbox.
export function wireLayerControls(layerMap, landformsUrl) {
  document.querySelectorAll('[data-layer]').forEach((input) => {
    input.addEventListener('change', () => {
      const key = input.dataset.layer;
      layerMap[key].setVisible(input.checked);
      const legendId = LEGEND_IDS[key];
      if (legendId) document.getElementById(legendId).style.display = input.checked ? '' : 'none';
      if (key === 'landforms') {
        if (input.checked) {
          reloadLandforms(landformsUrl);
        } else {
          clearLandforms();
        }
      }
    });
  });

  document.querySelectorAll('[name="basemap"]').forEach((radio) => {
    radio.addEventListener('change', () => {
      if (radio.checked) basemapLayer.setSource(BASEMAPS[radio.value]);
    });
  });

  document.querySelectorAll('.ls-opacity').forEach((slider) => {
    slider.addEventListener('input', () => {
      layerMap[slider.dataset.opacityFor].setOpacity(Number(slider.value));
    });
  });
}
