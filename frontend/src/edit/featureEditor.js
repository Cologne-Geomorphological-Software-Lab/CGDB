import Draw from 'ol/interaction/Draw.js';
import Modify from 'ol/interaction/Modify.js';
import Snap from 'ol/interaction/Snap.js';
import DoubleClickZoom from 'ol/interaction/DoubleClickZoom.js';

import { map } from '../map/mapInstance.js';
import { geojsonFormat } from '../utils/geojsonFormat.js';
import { getCsrfToken } from '../utils/csrf.js';
import { clearValidationError, showValidationError } from './validationErrors.js';

// Same fix as measure/measureTool.js: re-enabling this synchronously inside
// a drawend handler races the same click event finishing the sketch, so the
// map still zooms right as a new feature is drawn. Deferred to the next
// tick instead. Found and shared once for editing — Modify doesn't need
// this (it's drag-based, no dblclick), only Draw.
const doubleClickZoom = map
  .getInteractions()
  .getArray()
  .find((interaction) => interaction instanceof DoubleClickZoom);

/**
 * A shared Draw+Modify+Snap lifecycle wired to one display source and one
 * DRF endpoint. One instance per editable layer (study areas, transects,
 * locations) — never shared across sources.
 *
 * @param {object} opts
 * @param {import('ol/source/Vector.js').default} opts.source - the layer's
 *   own display source (e.g. studyAreaSource) — edits happen in place, on
 *   the same features already shown on the map.
 * @param {string} opts.geomType - OL geometry type for Draw ('Polygon',
 *   'MultiLineString', 'Point').
 * @param {string} opts.geomFieldName - the write serializer's geometry
 *   field name ('geometry', 'multiline', 'location').
 * @param {string} opts.listUrl - POST target for creating a new feature.
 * @param {(id: number) => string} opts.detailUrl - PATCH target for an
 *   existing feature.
 * @param {boolean} opts.allowCreate - false for Location (reshape-only).
 * @param {() => Promise<object|null>} [opts.onNeedProperties] - prompts for
 *   the non-geometry fields a new feature needs (e.g. label/project);
 *   resolves null if the user cancels. Required when allowCreate is true.
 */
export function createFeatureEditor({
  source,
  geomType,
  geomFieldName,
  listUrl,
  detailUrl,
  allowCreate,
  onNeedProperties,
}) {
  let drawInteraction = null;
  let modifyInteraction = null;
  let snapInteraction = null;

  async function saveFeature(feature, { isNew }) {
    const geometry = geojsonFormat.writeGeometryObject(feature.getGeometry());
    const payload = { [geomFieldName]: geometry };

    if (isNew) {
      const extra = await onNeedProperties();
      if (!extra) {
        source.removeFeature(feature);
        return;
      }
      Object.assign(payload, extra);
    }

    // OpenLayers' GeoJSON reader surfaces a Feature's top-level "id" via
    // getId(), not as a regular property — GeoFeatureModelSerializer places
    // "id" there (not inside "properties"), per the GeoJSON spec.
    const id = feature.getId();
    const url = isNew ? listUrl : detailUrl(id);
    const method = isNew ? 'POST' : 'PATCH';

    try {
      const resp = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(payload),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        showValidationError(data);
        if (isNew) source.removeFeature(feature);
        return;
      }
      if (isNew && data.id != null) feature.setId(data.id);
      feature.set('cgdbPending', false);
      clearValidationError();
    } catch {
      showValidationError('Network error — could not save.');
      if (isNew) source.removeFeature(feature);
    }
  }

  function start() {
    modifyInteraction = new Modify({ source });
    map.addInteraction(modifyInteraction);
    modifyInteraction.on('modifyend', (evt) => {
      evt.features.forEach((feature) => saveFeature(feature, { isNew: false }));
    });

    if (allowCreate) {
      drawInteraction = new Draw({ source, type: geomType });
      map.addInteraction(drawInteraction);
      drawInteraction.on('drawstart', (evt) => {
        evt.feature.set('cgdbPending', true);
      });
      drawInteraction.on('drawend', (evt) => {
        setTimeout(() => doubleClickZoom?.setActive(true), 0);
        saveFeature(evt.feature, { isNew: true });
      });
      doubleClickZoom?.setActive(false);

      // Added after Draw/Modify, per OL's interaction-ordering requirement.
      snapInteraction = new Snap({ source });
      map.addInteraction(snapInteraction);
    }
  }

  function stop() {
    [drawInteraction, modifyInteraction, snapInteraction].forEach((interaction) => {
      if (interaction) map.removeInteraction(interaction);
    });
    drawInteraction = null;
    modifyInteraction = null;
    snapInteraction = null;
    doubleClickZoom?.setActive(true);
    clearValidationError();
  }

  return { start, stop };
}
