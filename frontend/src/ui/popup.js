import { popup, popupEl } from '../map/mapInstance.js';
import { esc } from '../utils/esc.js';
import { fetchFeatureInfoHtml } from '../layers/wmsOverlays.js';

export function showPopup(coordinate, html) {
  document.getElementById('cgdb-popup-content').innerHTML = html;
  popupEl.style.display = 'block';
  popup.setPosition(coordinate);
}

export function hidePopup() {
  popupEl.style.display = 'none';
  popup.setPosition(undefined);
}

export function wirePopupClose() {
  document.getElementById('cgdb-popup-close').addEventListener('click', hidePopup);
}

function buildLocationPopup(p) {
  const badge = p.data_source === 'literature'
    ? '<span class="badge badge-literature">Literature</span>'
    : '<span class="badge badge-internal">Internal</span>';
  let rows = '';
  if (p.location_type_display) rows += `<div class="popup-row"><span class="popup-label">Category</span>${esc(p.location_type_display)}</div>`;
  if (p.project) rows += `<div class="popup-row"><span class="popup-label">Project</span>${esc(p.project)}</div>`;
  if (p.campaign) rows += `<div class="popup-row"><span class="popup-label">Campaign</span>${esc(p.campaign)}</div>`;
  if (p.date_of_record) rows += `<div class="popup-row"><span class="popup-label">Date</span>${esc(p.date_of_record)}</div>`;
  if (p.altitude != null) rows += `<div class="popup-row"><span class="popup-label">Altitude</span>${esc(p.altitude)} m</div>`;
  if (p.exposure_type) rows += `<div class="popup-row"><span class="popup-label">Exposure</span>${esc(p.exposure_type)}</div>`;
  let analyses = '';
  if (p.sample_count > 0) {
    analyses = `<div class="popup-analyses">${p.sample_count} sample(s)`;
    if (p.luminescence_count) analyses += ` &middot; ${p.luminescence_count} OSL/IRSL`;
    if (p.grain_size_count) analyses += ` &middot; ${p.grain_size_count} grain size`;
    analyses += '</div>';
  }
  return `<strong>${esc(p.identifier || '—')}</strong>${rows}${badge}${analyses}`
    + `<div style="margin-top:7px"><a href="${esc(p.admin_url)}">Open in admin &rarr;</a></div>`;
}

function buildStudyAreaPopup(p) {
  let rows = '';
  if (p.project) rows += `<div class="popup-row"><span class="popup-label">Project</span>${esc(p.project)}</div>`;
  if (p.climate_koeppen_display) rows += `<div class="popup-row"><span class="popup-label">Köppen</span>${esc(p.climate_koeppen_display)}</div>`;
  if (p.ecozone_schultz_display) rows += `<div class="popup-row"><span class="popup-label">Ecozone</span>${esc(p.ecozone_schultz_display)}</div>`;
  return `<strong>${esc(p.label || '—')}</strong>${rows}`
    + `<div style="margin-top:7px"><a href="${esc(p.admin_url)}">Open in admin &rarr;</a></div>`;
}

function buildTransectPopup(p) {
  let rows = '';
  if (p.study_area) rows += `<div class="popup-row"><span class="popup-label">Study Area</span>${esc(p.study_area)}</div>`;
  if (p.campaign) rows += `<div class="popup-row"><span class="popup-label">Campaign</span>${esc(p.campaign)}</div>`;
  return `<strong>${esc(p.identifier || '—')}</strong>${rows}`
    + `<div style="margin-top:7px"><a href="${esc(p.admin_url)}">Open in admin &rarr;</a></div>`;
}

function buildClusterPopup(features) {
  const items = features.slice(0, 20).map((f) => {
    const p = f.getProperties();
    const projectLabel = p.project
      ? ` <span style="color:#9ca3af;font-size:10px;">(${esc(p.project)})</span>`
      : '';
    return `<li><a href="${esc(p.admin_url)}">${esc(p.identifier || '—')}</a>${projectLabel}</li>`;
  });
  const extra = features.length > 20
    ? `<li style="color:#9ca3af;">…and ${features.length - 20} more</li>`
    : '';
  return `<strong>${features.length} locations</strong><ul class="cluster-list">${items.join('')}${extra}</ul>`;
}

function buildLandformPopup(p) {
  let rows = '';
  if (p.name_str) rows += `<div class="popup-row"><span class="popup-label">Name</span>${esc(p.name_str)}</div>`;
  if (p.continent) rows += `<div class="popup-row"><span class="popup-label">Continent</span>${esc(p.continent)}</div>`;
  if (p.division) rows += `<div class="popup-row"><span class="popup-label">Division</span>${esc(p.division)}</div>`;
  if (p.province) rows += `<div class="popup-row"><span class="popup-label">Province</span>${esc(p.province)}</div>`;
  if (p.murphy_code) rows += `<div class="popup-row"><span class="popup-label">Code</span>${esc(p.murphy_code)}</div>`;
  if (p.glaciate) rows += `<div class="popup-row"><span class="popup-label">Glaciation</span>${esc(p.glaciate)}</div>`;
  return `<strong>${esc(p.name_str || 'Landform')}</strong>${rows}`;
}

// Wires the map click handler: dispatches to the right popup builder for
// whichever vector layer was hit, or falls back to a WMS GetFeatureInfo
// lookup (via the server-side proxy) when nothing vector-based was clicked.
export function wireClickHandler(map, layers, wmsProxyUrl) {
  const { locationsLayer, studyAreasLayer, transectsLayer, landformsLayer } = layers;

  map.on('click', (evt) => {
    let hit = false;

    map.forEachFeatureAtPixel(
      evt.pixel,
      (feature, layer) => {
        if (hit) return;
        if (layer === locationsLayer) {
          const inner = feature.get('features');
          if (!inner) return;
          if (inner.length > 1) {
            showPopup(evt.coordinate, buildClusterPopup(inner));
          } else {
            showPopup(evt.coordinate, buildLocationPopup(inner[0].getProperties()));
          }
          hit = true;
        }
        if (layer === studyAreasLayer) {
          showPopup(evt.coordinate, buildStudyAreaPopup(feature.getProperties()));
          hit = true;
        }
        if (layer === transectsLayer) {
          showPopup(evt.coordinate, buildTransectPopup(feature.getProperties()));
          hit = true;
        }
        if (layer === landformsLayer) {
          showPopup(evt.coordinate, buildLandformPopup(feature.getProperties()));
          hit = true;
        }
      },
      { hitTolerance: 6 },
    );

    if (hit) return;

    fetchFeatureInfoHtml(map, evt.coordinate, wmsProxyUrl).then((html) => {
      if (html) {
        showPopup(evt.coordinate, html);
      } else {
        hidePopup();
      }
    });
  });
}
