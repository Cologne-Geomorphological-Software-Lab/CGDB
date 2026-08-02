import { resolve } from 'node:path';
import { defineConfig } from 'vite';

// Built assets are served by Django's staticfiles app from static/dist/,
// which is already inside STATICFILES_DIRS (see prototype/local_settings.py).
export default defineConfig({
  base: '/static/dist/',
  build: {
    manifest: true,
    outDir: resolve(__dirname, '../static/dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        // Map dashboard (prototype/views.py's map_dashboard).
        main: resolve(__dirname, 'src/main.js'),
        // Location change form's satellite preview widget
        // (field_data/admin.py's LocationAdmin.map_preview) — a separate
        // entry since it's a different Django admin page, not the dashboard.
        adminLocationPreview: resolve(__dirname, 'src/adminLocationPreview.js'),
      },
    },
  },
  server: {
    // Explicit IPv4 host: Vite's default ('localhost') can resolve to the
    // IPv6 loopback only on some machines, leaving the dev server unreachable
    // (or reachable only after a slow Happy-Eyeballs fallback) at the IPv4
    // address django-vite's script tags below actually point at.
    host: '127.0.0.1',
    // django-vite's dev-mode <script> tags point at this origin.
    origin: 'http://127.0.0.1:5173',
  },
});
