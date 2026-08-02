import { clearMeasure, startMeasure } from '../measure/measureTool.js';

export function initMeasureControls(toggleBtn) {
  const container = document.getElementById('cgdb-measure');
  const distanceBtn = document.getElementById('cgdb-measure-distance');
  const areaBtn = document.getElementById('cgdb-measure-area');
  const clearBtn = document.getElementById('cgdb-measure-clear');
  if (!container || !distanceBtn || !areaBtn || !clearBtn || !toggleBtn) return;

  toggleBtn.addEventListener('click', () => {
    container.hidden = !container.hidden;
  });

  distanceBtn.addEventListener('click', () => {
    distanceBtn.classList.add('active');
    areaBtn.classList.remove('active');
    startMeasure('LineString');
  });

  areaBtn.addEventListener('click', () => {
    areaBtn.classList.add('active');
    distanceBtn.classList.remove('active');
    startMeasure('Polygon');
  });

  clearBtn.addEventListener('click', () => {
    distanceBtn.classList.remove('active');
    areaBtn.classList.remove('active');
    clearMeasure();
  });
}
