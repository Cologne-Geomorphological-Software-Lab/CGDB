import { basemapLayer } from '../map/mapInstance.js';
import { BASEMAP_GALLERY, BASEMAPS } from '../map/basemaps.js';
import {
  CLUSTER_LEGEND,
  LANDFORM_CONTINENT_LEGEND,
  LITERATURE_LEGEND,
  LOCATION_TYPE_LEGEND,
  STUDY_AREA_LEGEND,
  TRANSECT_LEGEND,
} from '../styles/legendContent.js';
import { esc } from '../utils/esc.js';

function pointSwatch({ shape, fill, stroke }, size = 14) {
  const c = size / 2;
  const r = size / 2 - 1.5;
  if (shape === 'circle') {
    return `<svg width="${size}" height="${size}"><circle cx="${c}" cy="${c}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="1.5"/></svg>`;
  }
  if (shape === 'square') {
    return `<svg width="${size}" height="${size}"><rect x="1.5" y="1.5" width="${size - 3}" height="${size - 3}" rx="1" fill="${fill}" stroke="${stroke}" stroke-width="1.5"/></svg>`;
  }
  if (shape === 'diamond') {
    return `<svg width="${size}" height="${size}"><polygon points="${c},1.5 ${size - 1.5},${c} ${c},${size - 1.5} 1.5,${c}" fill="${fill}" stroke="${stroke}" stroke-width="1.5"/></svg>`;
  }
  return `<svg width="${size}" height="${size}"><polygon points="${c},1.5 ${size - 1.5},${size - 1.5} 1.5,${size - 1.5}" fill="${fill}" stroke="${stroke}" stroke-width="1.5"/></svg>`;
}

function clusterSwatch(size = 14) {
  const c = size / 2;
  const r = size / 2 - 0.5;
  return `<svg width="${size}" height="${size}"><circle cx="${c}" cy="${c}" r="${r}" fill="${CLUSTER_LEGEND.fill}" stroke="${CLUSTER_LEGEND.stroke}" stroke-width="1.5"/><text x="${c}" y="${c + 3.5}" text-anchor="middle" font-size="7" fill="#fff" font-weight="700">n</text></svg>`;
}

function lineSwatch({ stroke, dash }, width = 24, height = 14) {
  const dashAttr = dash ? ' stroke-dasharray="5,3"' : '';
  return `<svg width="${width}" height="${height}"><line x1="0" y1="${height / 2}" x2="${width}" y2="${height / 2}" stroke="${stroke}" stroke-width="2"${dashAttr}/></svg>`;
}

function areaSwatch({ fill, stroke }, width = 24, height = 14) {
  return `<svg width="${width}" height="${height}"><rect x="0" y="${height / 2 - 3}" width="${width}" height="6" fill="${fill}" stroke="${stroke}" stroke-width="1.2"/></svg>`;
}

function outlineSwatch({ stroke }, width = 24, height = 14) {
  return `<svg width="${width}" height="${height}"><rect x="0" y="${height / 2 - 3}" width="${width}" height="6" fill="none" stroke="${stroke}" stroke-width="1.5"/></svg>`;
}

function legendRow(swatchHtml, label) {
  return `<div class="cgdb-legend-row">${swatchHtml}<span>${esc(label)}</span></div>`;
}

function populateInlineSwatches() {
  const studyAreaEl = document.querySelector('[data-swatch="study_areas"]');
  if (studyAreaEl) studyAreaEl.innerHTML = areaSwatch(STUDY_AREA_LEGEND, 18, 14);

  const transectEl = document.querySelector('[data-swatch="transects"]');
  if (transectEl) transectEl.innerHTML = lineSwatch(TRANSECT_LEGEND, 18, 14);
}

function populateExpandableLegends() {
  const locationsLegend = document.querySelector('[data-legend-for="locations"]');
  if (locationsLegend) {
    const rows = [
      ...LOCATION_TYPE_LEGEND.map((entry) => legendRow(pointSwatch(entry), entry.label)),
      legendRow(pointSwatch({ ...LITERATURE_LEGEND, shape: 'circle' }), LITERATURE_LEGEND.label),
      legendRow(clusterSwatch(), CLUSTER_LEGEND.label),
    ];
    locationsLegend.innerHTML = rows.join('');
  }

  const landformsLegend = document.querySelector('[data-legend-for="landforms"]');
  if (landformsLegend) {
    landformsLegend.innerHTML = LANDFORM_CONTINENT_LEGEND.map((entry) =>
      legendRow(outlineSwatch(entry), entry.label),
    ).join('');
  }
}

function wireLegendToggles() {
  document.querySelectorAll('[data-legend-toggle]').forEach((btn) => {
    const key = btn.dataset.legendToggle;
    const panel = document.querySelector(`[data-legend-for="${key}"]`);
    if (!panel) return;
    btn.addEventListener('click', () => {
      const isHidden = panel.hasAttribute('hidden');
      if (isHidden) {
        panel.removeAttribute('hidden');
      } else {
        panel.setAttribute('hidden', '');
      }
      btn.classList.toggle('expanded', isHidden);
    });
  });
}

function wireBasemapGallery() {
  const gallery = document.getElementById('basemap-gallery');
  if (!gallery) return;
  gallery.innerHTML = BASEMAP_GALLERY.map(
    (bm, i) => `
      <button type="button" class="basemap-thumb${i === 0 ? ' active' : ''}" data-basemap="${bm.key}" title="${esc(bm.label)}">
        <img src="${bm.thumbnail}" alt="" loading="lazy">
        <span>${esc(bm.label)}</span>
      </button>`,
  ).join('');

  gallery.querySelectorAll('[data-basemap]').forEach((btn) => {
    btn.addEventListener('click', () => {
      gallery.querySelectorAll('[data-basemap]').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      basemapLayer.setSource(BASEMAPS[btn.dataset.basemap]);
    });
  });
}

const LEGEND_TOGGLE_VISIBILITY_KEYS = new Set(['bgr_geo', 'macrostrat']);

function wireLayerVisibility(layerMap) {
  document.querySelectorAll('[data-layer]').forEach((input) => {
    input.addEventListener('change', () => {
      const key = input.dataset.layer;
      layerMap[key].setVisible(input.checked);
      // BGR/Macrostrat's legend content is only meaningful once the layer
      // is actually on — collapse it again when the layer is hidden.
      if (!input.checked && LEGEND_TOGGLE_VISIBILITY_KEYS.has(key)) {
        document.querySelector(`[data-legend-for="${key}"]`)?.setAttribute('hidden', '');
      }
      // Landforms visibility alone is enough — VectorTileLayer handles
      // viewport-driven tile loading natively, unlike the old GeoJSON
      // bbox-fetch approach this replaced.
    });
  });

  document.querySelectorAll('.ls-opacity').forEach((slider) => {
    slider.addEventListener('input', () => {
      layerMap[slider.dataset.opacityFor].setOpacity(Number(slider.value));
    });
  });
}

export function setLayerLoading(layerKey, isLoading) {
  const spinner = document.querySelector(`[data-spinner="${layerKey}"]`);
  if (!spinner) return;
  spinner.toggleAttribute('hidden', !isLoading);
}

export function initLayersPanel(layerMap) {
  populateInlineSwatches();
  populateExpandableLegends();
  wireLegendToggles();
  wireBasemapGallery();
  wireLayerVisibility(layerMap);
}
