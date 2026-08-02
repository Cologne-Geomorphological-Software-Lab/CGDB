// Read the CSRF token from Django's csrftoken cookie (CSRF_COOKIE_HTTPONLY
// defaults to False, so this is readable client-side). Used by Phase 4's
// edit round-trip; harmless to have available now.
export function getCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}
