import XYZ from 'ol/source/XYZ.js';

export const BASEMAPS = {
  esri_sat: new XYZ({
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    maxZoom: 17,
    attributions: 'Tiles &copy; Esri',
  }),
  google_sat: new XYZ({
    url: 'https://mt0.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    maxZoom: 20,
    attributions: '&copy; Google',
  }),
  carto_light: new XYZ({
    url: 'https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    maxZoom: 19,
    attributions: '&copy; <a href="https://carto.com">CARTO</a>',
  }),
  carto_dark: new XYZ({
    url: 'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    maxZoom: 19,
    attributions: '&copy; <a href="https://carto.com">CARTO</a>',
  }),
  topo: new XYZ({
    url: 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
    maxZoom: 17,
    attributions: '&copy; OpenTopoMap contributors',
  }),
};

// Basemap gallery metadata: a fixed low-zoom tile from each provider's own
// server, used directly as a thumbnail <img src>. No binary assets to
// maintain — always reflects what the provider actually renders.
export const BASEMAP_GALLERY = [
  {
    key: 'esri_sat',
    label: 'ESRI Satellite',
    thumbnail: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/2/1/2',
  },
  {
    key: 'carto_light',
    label: 'CartoDB Light',
    thumbnail: 'https://basemaps.cartocdn.com/light_all/2/2/1.png',
  },
  {
    key: 'carto_dark',
    label: 'CartoDB Dark',
    thumbnail: 'https://basemaps.cartocdn.com/dark_all/2/2/1.png',
  },
  {
    key: 'topo',
    label: 'OpenTopoMap',
    thumbnail: 'https://tile.opentopomap.org/2/2/1.png',
  },
  {
    key: 'google_sat',
    label: 'Google Satellite',
    thumbnail: 'https://mt0.google.com/vt/lyrs=s&x=2&y=1&z=2',
  },
];
