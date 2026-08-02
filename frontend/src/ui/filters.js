import { setVisibleLocations } from '../layers/locations.js';

const FILTER_CONTROL_IDS = ['cb-internal', 'cb-literature', 'project-select', 'campaign-select', 'type-select'];

export function applyFilter(allFeatures) {
  const showInternal = document.getElementById('cb-internal').checked;
  const showLiterature = document.getElementById('cb-literature').checked;
  const project = document.getElementById('project-select').value;
  const campaign = document.getElementById('campaign-select').value;
  const type = document.getElementById('type-select').value;

  const filtered = allFeatures.filter((f) => {
    const p = f.getProperties();
    if (p.data_source === 'internal' && !showInternal) return false;
    if (p.data_source === 'literature' && !showLiterature) return false;
    if (project && p.project !== project) return false;
    if (campaign && p.campaign !== campaign) return false;
    if (type && p.location_type !== type) return false;
    return true;
  });

  setVisibleLocations(filtered);
  document.getElementById('cgdb-filter-count').textContent = `${filtered.length} location(s) shown`;
}

export function populateFilterDropdowns(features) {
  const projects = [];
  const campaigns = [];
  const types = [];
  const typeLabels = {};

  features.forEach((f) => {
    const p = f.getProperties();
    if (p.project && !projects.includes(p.project)) projects.push(p.project);
    if (p.campaign && !campaigns.includes(p.campaign)) campaigns.push(p.campaign);
    if (p.location_type && !types.includes(p.location_type)) types.push(p.location_type);
    if (p.location_type) typeLabels[p.location_type] = p.location_type_display;
  });
  projects.sort();
  campaigns.sort();
  types.sort();

  const pSel = document.getElementById('project-select');
  projects.forEach((v) => {
    const o = document.createElement('option');
    o.value = v;
    o.text = v;
    pSel.add(o);
  });
  const cSel = document.getElementById('campaign-select');
  campaigns.forEach((v) => {
    const o = document.createElement('option');
    o.value = v;
    o.text = v;
    cSel.add(o);
  });
  const tSel = document.getElementById('type-select');
  types.forEach((v) => {
    const o = document.createElement('option');
    o.value = v;
    o.text = typeLabels[v] || v;
    tSel.add(o);
  });
}

export function wireFilterControls(onChange) {
  FILTER_CONTROL_IDS.forEach((id) => {
    document.getElementById(id).addEventListener('change', onChange);
  });
}
