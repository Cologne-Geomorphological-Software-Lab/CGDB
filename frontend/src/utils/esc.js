// Escape a value for safe insertion into innerHTML.
export function esc(value) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(value == null ? '' : String(value)));
  return d.innerHTML;
}
