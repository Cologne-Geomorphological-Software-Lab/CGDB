import { studyAreaSource } from '../layers/studyAreas.js';
import { createFeatureEditor } from './featureEditor.js';
import { promptForFields } from './propertiesModal.js';

async function fetchAddableProjects() {
  const resp = await fetch('/api/v1/projects/');
  if (!resp.ok) return [];
  const data = await resp.json();
  const results = data.results ?? data;
  return results.map((p) => ({ value: p.id, label: p.title }));
}

export function createStudyAreaEditor() {
  return createFeatureEditor({
    source: studyAreaSource,
    geomType: 'Polygon',
    geomFieldName: 'geometry',
    listUrl: '/api/v1/study-areas/',
    detailUrl: (id) => `/api/v1/study-areas/${id}/`,
    allowCreate: true,
    onNeedProperties: async () => {
      const projects = await fetchAddableProjects();
      if (!projects.length) {
        window.alert('No projects available to add a study area to.');
        return null;
      }
      return promptForFields('New Study Area', [
        { name: 'label', label: 'Label' },
        { name: 'project', label: 'Project', type: 'select', options: projects },
      ]);
    },
  });
}
