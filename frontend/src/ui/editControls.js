import { createLocationEditor } from '../edit/locationEditor.js';
import { createStudyAreaEditor } from '../edit/studyAreaEditor.js';
import { createTransectEditor } from '../edit/transectEditor.js';

// Draw/Modify/Snap interactions only run while their checkbox is on — never
// live on the default view-only dashboard, per the same lesson Phase 3's
// measurement tools already established (unexpected interactions firing on
// clicks a user didn't mean as edits).
export function initEditControls(toggleBtn) {
  const container = document.getElementById('cgdb-edit');
  const studyAreaCb = document.getElementById('cgdb-edit-study-areas');
  const transectCb = document.getElementById('cgdb-edit-transects');
  const locationCb = document.getElementById('cgdb-edit-locations');
  if (!toggleBtn || !container || !studyAreaCb || !transectCb || !locationCb) return;

  const editors = {
    studyAreas: createStudyAreaEditor(),
    transects: createTransectEditor(),
    locations: createLocationEditor(),
  };

  function stopAll() {
    studyAreaCb.checked = false;
    transectCb.checked = false;
    locationCb.checked = false;
    editors.studyAreas.stop();
    editors.transects.stop();
    editors.locations.stop();
  }

  toggleBtn.addEventListener('click', () => {
    const opening = container.hidden;
    container.hidden = !opening;
    if (!opening) stopAll(); // closing the panel turns editing off entirely
  });

  studyAreaCb.addEventListener('change', () => {
    if (studyAreaCb.checked) editors.studyAreas.start();
    else editors.studyAreas.stop();
  });
  transectCb.addEventListener('change', () => {
    if (transectCb.checked) editors.transects.start();
    else editors.transects.stop();
  });
  locationCb.addEventListener('change', () => {
    if (locationCb.checked) editors.locations.start();
    else editors.locations.stop();
  });
}
