// Keep in sync with the responsive breakpoint in styles/dashboard.css.
const MOBILE_BREAKPOINT = 768;

export function wireSidebarTabs() {
  document.querySelectorAll('.sidebar-tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sidebar-tab').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.sidebar-panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
  });
}

export function wireSidebarToggle(map) {
  const sidebar = document.getElementById('cgdb-sidebar');
  const btn = document.getElementById('cgdb-sidebar-toggle');
  const icon = btn.querySelector('.material-symbols-outlined');

  // Below the responsive breakpoint the sidebar overlays the map (see
  // dashboard.css) rather than compressing it — start collapsed there so
  // the map is usable immediately instead of reduced to a sliver.
  let sidebarOpen = window.innerWidth > MOBILE_BREAKPOINT;
  sidebar.classList.toggle('collapsed', !sidebarOpen);
  btn.classList.toggle('sidebar-open', sidebarOpen);
  icon.textContent = sidebarOpen ? 'chevron_left' : 'chevron_right';

  btn.addEventListener('click', () => {
    sidebarOpen = !sidebarOpen;
    sidebar.classList.toggle('collapsed', !sidebarOpen);
    btn.classList.toggle('sidebar-open', sidebarOpen);
    icon.textContent = sidebarOpen ? 'chevron_left' : 'chevron_right';
    btn.setAttribute('aria-label', sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar');
    setTimeout(() => map.updateSize(), 200);
  });
}
