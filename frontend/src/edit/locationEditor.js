import { locationSource } from '../layers/locations.js';
import { createFeatureEditor } from './featureEditor.js';

// Update-only: reshapes/relocates an existing marker. Drawing a bare point
// with no other context is a poor UX fit versus the existing admin create
// form, so this never allows creating new Location records.
//
// Targets locationSource (the raw, unclustered source), not the rendered
// locationsLayer's Cluster-wrapped source — Modify hit-tests geometry
// coordinates directly, independent of how a layer's style groups nearby
// points visually, so this works correctly even while zoomed out enough
// that a point renders merged into a cluster bubble. For precise dragging,
// zoom in until clustering resolves to individual markers.
export function createLocationEditor() {
  return createFeatureEditor({
    source: locationSource,
    geomType: 'Point',
    geomFieldName: 'location',
    listUrl: '',
    detailUrl: (id) => `/api/v1/locations/${id}/`,
    allowCreate: false,
  });
}
