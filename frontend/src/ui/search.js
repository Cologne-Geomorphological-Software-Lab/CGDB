import { fromLonLat } from 'ol/proj.js';

import { map } from '../map/mapInstance.js';

// Nominatim (OpenStreetMap's public geocoder): no API key, but its usage
// policy requires a descriptive request and no autocomplete-style spamming —
// this only fires on explicit Enter, never per keystroke. Attribution is
// covered by the map's Attribution control (see map/mapInstance.js) plus the
// "OpenStreetMap contributors" credit shown alongside results here.
const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';

async function geocode(query) {
  const url = `${NOMINATIM_URL}?format=json&limit=1&q=${encodeURIComponent(query)}`;
  const resp = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!resp.ok) throw new Error(`Nominatim HTTP ${resp.status}`);
  const results = await resp.json();
  return results[0] || null;
}

export function initSearch(toggleBtn) {
  const container = document.getElementById('cgdb-search');
  const input = document.getElementById('cgdb-search-input');
  const statusEl = document.getElementById('cgdb-search-status');
  if (!container || !input || !statusEl || !toggleBtn) return;

  function show() {
    container.hidden = false;
    input.focus();
  }
  function hide() {
    container.hidden = true;
    input.value = '';
    statusEl.textContent = '';
  }

  toggleBtn.addEventListener('click', () => {
    if (container.hidden) show();
    else hide();
  });

  input.addEventListener('keydown', async (evt) => {
    if (evt.key === 'Escape') {
      hide();
      return;
    }
    if (evt.key !== 'Enter') return;
    const query = input.value.trim();
    if (!query) return;

    statusEl.textContent = 'Searching…';
    try {
      const result = await geocode(query);
      if (!result) {
        statusEl.textContent = 'No results found.';
        return;
      }
      const center = fromLonLat([Number(result.lon), Number(result.lat)]);
      map.getView().animate({ center, zoom: 12, duration: 400 });
      statusEl.textContent = `${result.display_name} — © OpenStreetMap contributors`;
    } catch {
      statusEl.textContent = 'Search failed — try again.';
    }
  });
}
