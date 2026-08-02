"""Auto-launch the Vite dev server alongside `manage.py runserver`.

Without this, `manage.py runserver` alone leaves django-vite's dev-mode
script tags pointing at a Vite dev server that isn't running, which shows up
in the browser as a confusing cross-origin/module-load error rather than an
obvious "connection refused".

Hooked from PrototypeConfig.ready() rather than overriding the `runserver`
command: django.contrib.staticfiles already provides its own `runserver`
override and — because it's listed earlier in INSTALLED_APPS — wins Django's
command-priority resolution over a same-named command in this app, so
subclassing runserver here would silently never run.
"""

from __future__ import annotations

import atexit
import os
import subprocess
import sys

from django.conf import settings

_FRONTEND_DIR = settings.BASE_DIR / "frontend"


def start_if_appropriate() -> None:
    """Start `npm run dev` for the map dashboard frontend.

    Only if this process is actually the one serving `manage.py runserver`
    with Vite dev mode on.
    """
    if "runserver" not in sys.argv:
        return

    dev_mode = (
        getattr(settings, "DJANGO_VITE", {})
        .get("default", {})
        .get("dev_mode", False)
    )
    if not dev_mode:
        return

    # The autoreloader re-execs `manage.py runserver` in a child process
    # (with RUN_MAIN=true); only that child — or a --noreload run, which
    # never re-execs — should spawn the Vite subprocess, or every reload
    # would spawn a duplicate on top of the previous one.
    reloader_enabled = "--noreload" not in sys.argv
    if reloader_enabled and os.environ.get("RUN_MAIN") != "true":
        return

    if not (_FRONTEND_DIR / "node_modules").exists():
        print(  # noqa: T201 — startup diagnostic, no logger configured this early
            f"[vite] Skipping dev server: {_FRONTEND_DIR / 'node_modules'} "
            "not found. Run `npm install` in frontend/ first.",
            file=sys.stderr,
        )
        return

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        process = subprocess.Popen(  # noqa: S603 — fixed argv, no shell, no user input
            [npm_cmd, "run", "dev"],
            cwd=_FRONTEND_DIR,
        )
    except OSError as exc:
        print(f"[vite] Could not start dev server: {exc}", file=sys.stderr)  # noqa: T201
        return

    atexit.register(process.terminate)
    print(  # noqa: T201
        f"[vite] Dev server starting (pid={process.pid}), "
        "see frontend/ for its own output."
    )
