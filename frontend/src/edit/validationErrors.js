// Surfaces DRF write errors as a visible toast near the map — never just
// console.error, per VECTOR_EDITING.md's guidance that a failed save must
// be obvious to the person who just drew something.
let errorEl = null;
let hideTimer = null;

function ensureErrorEl() {
  if (errorEl) return errorEl;
  errorEl = document.createElement('div');
  errorEl.id = 'cgdb-edit-error';
  errorEl.hidden = true;
  document.getElementById('cgdb-map-zone')?.appendChild(errorEl);
  return errorEl;
}

function formatErrorBody(body) {
  if (typeof body === 'string') return body;
  if (body && typeof body === 'object') {
    const parts = Object.entries(body).map(([field, messages]) => {
      const text = Array.isArray(messages) ? messages.join(' ') : String(messages);
      return field === 'detail' ? text : `${field}: ${text}`;
    });
    if (parts.length) return parts.join(' — ');
  }
  return 'Save failed.';
}

export function showValidationError(body) {
  const el = ensureErrorEl();
  el.textContent = formatErrorBody(body);
  el.hidden = false;
  clearTimeout(hideTimer);
  hideTimer = setTimeout(() => {
    el.hidden = true;
  }, 6000);
}

export function clearValidationError() {
  if (errorEl) errorEl.hidden = true;
  clearTimeout(hideTimer);
}
