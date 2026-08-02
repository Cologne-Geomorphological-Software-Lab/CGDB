import { transectSource } from '../layers/transects.js';
import { createFeatureEditor } from './featureEditor.js';
import { promptForFields } from './propertiesModal.js';

async function fetchAddableStudyAreas() {
  // .../map/ returns a plain (unpaginated) FeatureCollection scoped to
  // accessible projects — simpler and more predictable here than the
  // default list action's GeoJSON+pagination combination.
  const resp = await fetch('/api/v1/study-areas/map/');
  if (!resp.ok) return [];
  const data = await resp.json();
  return (data.features ?? []).map((f) => ({ value: f.id, label: f.properties.label }));
}

export function createTransectEditor() {
  return createFeatureEditor({
    source: transectSource,
    geomType: 'MultiLineString',
    geomFieldName: 'multiline',
    listUrl: '/api/v1/transects/',
    detailUrl: (id) => `/api/v1/transects/${id}/`,
    allowCreate: true,
    onNeedProperties: async () => {
      const studyAreas = await fetchAddableStudyAreas();
      if (!studyAreas.length) {
        window.alert('No study areas available — create one first.');
        return null;
      }
      return promptForFields('New Transect', [
        { name: 'identifier', label: 'Identifier' },
        { name: 'study_area', label: 'Study Area', type: 'select', options: studyAreas },
        { name: 'description', label: 'Description' },
      ]);
    },
  });
}
