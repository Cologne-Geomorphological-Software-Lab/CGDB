// Single source of truth for every symbol the map draws — both the actual
// OpenLayers styling (styles/mapStyles.js) and the inline per-layer legend
// (ui/layersPanel.js) read from here, so they can never drift apart like the
// old template's hand-copied SVG legend did.

export const LOCATION_TYPE_LEGEND = [
  {
    key: 'sampling_location',
    label: 'Sampling Location',
    shape: 'circle',
    fill: '#3b82f6',
    stroke: '#1d4ed8',
  },
  {
    key: 'camp',
    label: 'Camp / Infrastructure',
    shape: 'square',
    fill: '#f59e0b',
    stroke: '#d97706',
  },
  {
    key: 'weather_station',
    label: 'Weather / Survey',
    shape: 'diamond',
    fill: '#10b981',
    stroke: '#059669',
  },
  {
    key: 'observation',
    label: 'Observation',
    shape: 'triangle',
    fill: '#10b981',
    stroke: '#059669',
  },
  {
    key: 'other',
    label: 'Other',
    shape: 'diamond',
    fill: '#8b5cf6',
    stroke: '#7c3aed',
  },
];

// `road_access` and `infrastructure` share camp's symbol; `survey_point`
// shares weather_station's — same aliasing the old TYPE_FILL/STROKE/SHAPE
// maps had, kept so unrecognised-but-valid location types still render.
export const LOCATION_TYPE_ALIASES = {
  road_access: 'camp',
  infrastructure: 'camp',
  survey_point: 'weather_station',
};

export const LITERATURE_LEGEND = {
  label: 'Literature',
  shape: 'circle',
  fill: '#9ca3af',
  stroke: '#6b7280',
};

export const CLUSTER_LEGEND = {
  label: 'Cluster',
  fill: 'rgba(59,130,246,0.8)',
  stroke: '#1d4ed8',
};

export const LANDFORM_CONTINENT_LEGEND = [
  { label: 'North America', stroke: '#e63946' },
  { label: 'South America', stroke: '#f4a261' },
  { label: 'Europe', stroke: '#2a9d8f' },
  { label: 'Africa', stroke: '#e9c46a' },
  { label: 'Asia', stroke: '#457b9d' },
  { label: 'Oceania', stroke: '#6a4c93' },
  { label: 'Antarctica', stroke: '#adb5bd' },
];
export const LANDFORM_DEFAULT_STROKE = '#adb5bd';

export const STUDY_AREA_LEGEND = {
  label: 'Study Area',
  fill: 'rgba(16,185,129,0.15)',
  stroke: '#059669',
};

export const TRANSECT_LEGEND = {
  label: 'Transect',
  stroke: '#f97316',
  dash: true,
};

export function resolveLocationTypeEntry(locationType) {
  const key = LOCATION_TYPE_ALIASES[locationType] || locationType;
  return LOCATION_TYPE_LEGEND.find((entry) => entry.key === key) || LOCATION_TYPE_LEGEND.at(-1);
}
