import { INITIAL_CENTER, INITIAL_ZOOM, map, shellEl } from '../map/mapInstance.js';

function iconButton(icon, label) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'map-toolbar-btn';
  btn.setAttribute('aria-label', label);
  btn.title = label;
  btn.innerHTML = `<span class="material-symbols-outlined">${icon}</span>`;
  return btn;
}

function wireHome(toolbar) {
  const btn = iconButton('home', 'Reset view');
  btn.addEventListener('click', () => {
    map.getView().animate({ center: INITIAL_CENTER, zoom: INITIAL_ZOOM, duration: 300 });
  });
  toolbar.append(btn);
}

function wireFullscreen(toolbar) {
  const btn = iconButton('fullscreen', 'Fullscreen');
  const isFullscreen = () => document.fullscreenElement === shellEl;
  const sync = () => {
    btn.querySelector('.material-symbols-outlined').textContent = isFullscreen()
      ? 'fullscreen_exit'
      : 'fullscreen';
    btn.title = isFullscreen() ? 'Exit fullscreen' : 'Fullscreen';
  };
  btn.addEventListener('click', () => {
    if (isFullscreen()) {
      document.exitFullscreen();
    } else {
      shellEl.requestFullscreen();
    }
  });
  document.addEventListener('fullscreenchange', sync);
  toolbar.append(btn);
}

// This module only creates the buttons below — ui/search.js and
// ui/measureControls.js attach their own show/hide behaviour, since each
// owns its own panel's DOM/state.
function createSearchButton(toolbar) {
  const btn = iconButton('search', 'Search location');
  toolbar.append(btn);
  return btn;
}

function createMeasureButton(toolbar) {
  const btn = iconButton('straighten', 'Measure distance/area');
  toolbar.append(btn);
  return btn;
}

function createEditButton(toolbar) {
  const btn = iconButton('edit', 'Edit geometry');
  toolbar.append(btn);
  return btn;
}

// Returns the toggle buttons so ui/search.js, ui/measureControls.js, and
// ui/editControls.js can wire their own panels without this module needing
// to know about them. editBtn is null when canEdit is false — the server
// already decided the user can't save anything (prototype/views.py's
// map_dashboard), so the button isn't worth showing at all.
export function initToolbar(canEdit) {
  const toolbar = document.getElementById('cgdb-toolbar');
  if (!toolbar) return { searchBtn: null, measureBtn: null, editBtn: null };
  wireHome(toolbar);
  const searchBtn = createSearchButton(toolbar);
  const measureBtn = createMeasureButton(toolbar);
  const editBtn = canEdit ? createEditButton(toolbar) : null;
  wireFullscreen(toolbar);
  return { searchBtn, measureBtn, editBtn };
}
