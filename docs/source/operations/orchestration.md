# Data orchestration (optional)

CGDB includes an optional orchestration module based on [Dagster](https://dagster.io/). It runs the maintenance jobs (database backup, DuckDB export, integrity check) and is a starting point for your own pipelines: data ingestion, ETL, data quality checks or whole analysis pipelines. Adapt it to your IT environment.

There is no Dagster UI or webserver in this setup, in development or in production. Maintenance jobs are started from the Django admin ("Trigger selected maintenance job(s)"), which launches the run directly through `dagster job launch` and `DefaultRunLauncher`. No `run_coordinator` is configured, so runs aren't queued or throttled. Nothing depends on a UI, and nothing listens on a network port except Django itself. To inspect run history and logs, use the `dagster` CLI (for example `dagster run list` or `dagster run logs <run-id>`) with the same `DAGSTER_HOME`, or read `MaintenanceRun.log` and `result_file` in the admin.

## Setup

1. Dagster's dependencies are already part of the project's dependencies (`uv sync`); nothing needs to be installed separately.

2. Set the Dagster home directory:

   ```bash
   export DAGSTER_HOME=$(pwd)/orchestration/dagster_home
   ```

   By default, Dagster's run storage (`orchestration/dagster_home/dagster.yaml`) uses SQLite under `DAGSTER_HOME`; no further setup is needed. This is safe for CGDB's usage: a single daemon process and jobs started manually from the admin, without a scheduler or concurrent workers.

   **Optional: PostgreSQL** for more throughput (several concurrent workers, scheduled runs). In `orchestration/dagster_home/dagster.yaml`, comment out the `sqlite` storage block and uncomment the `postgres` block, then set the four credentials. This can be the same PostgreSQL server and credentials the rest of the deployment uses, with its own database (for example `dagster`):

   ```bash
   export DAGSTER_PG_USER=dagster
   export DAGSTER_PG_PASSWORD=...
   export DAGSTER_PG_HOST=localhost
   export DAGSTER_PG_DB=dagster
   ```

3. Start both processes with honcho. Development and production use the same two processes:

   ```bash
   honcho start
   ```

   - Django: <http://localhost:8000>
   - `dagster-daemon`: no UI and no listening port; it updates the status of runs started from the admin.

   Or start them one at a time: `honcho start web` and `honcho start daemon`.

   **Windows:** the process-group signal handling of `dagster-daemon run` targets POSIX and has not been tested on Windows. If it doesn't work there, run a maintenance job synchronously by hand: `python manage.py run_maintenance_job <backup|duckdb|integrity> --run-id <id>` (see `orchestration/management/commands/run_maintenance_job.py`).

(updating-to-the-daemon-based-setup)=
## Updating an existing deployment to the daemon-based setup

Older deployments started maintenance jobs with a detached `subprocess.Popen` from the admin, with no daemon and no dedicated Dagster run storage. To move such a deployment to the daemon-based setup, in this order:

1. **Deploy the new code** and reinstall the dependencies. `dagster` and `dagster-webserver` require `>=1.13.11`, `dagster-postgres` requires `>=0.29.11` (see `pyproject.toml`). No Django migrations are involved; this is a configuration change, not a schema change.

2. *(Only for PostgreSQL run storage, see above.)* **Create a database for Dagster's run storage** on the PostgreSQL server the app already uses, with a separate database name such as `dagster`. Dagster creates its schema on the first connection; no migration step is needed:

   ```sql
   CREATE DATABASE dagster;
   GRANT ALL PRIVILEGES ON DATABASE dagster TO app_db_user;  -- the database user of the app
   ```

3. *(Only for PostgreSQL run storage.)* **Set the four `DAGSTER_PG_*` environment variables** wherever the deployment's other environment variables live. `DAGSTER_HOME` is required either way, and enough on its own for the SQLite default.

4. **Run the daemon as its own supervised process**, next to whatever already runs Django. If Django is served by Apache with mod_wsgi, add a separate systemd unit for the daemon; Apache itself doesn't need to know about it. Run the daemon as the same user as your `WSGIDaemonProcess`: look up `user=` and `group=` on that directive in your Apache vhost configuration (`/etc/apache2/sites-available/*.conf`). Then create, for example, `/etc/systemd/system/cgdb-dagster-daemon.service`:

   ```ini
   [Unit]
   Description=CGDB Dagster Daemon
   After=network.target postgresql.service

   [Service]
   Type=simple
   User=<web-server-user>
   Group=<web-server-user>
   WorkingDirectory=<project-root>
   Environment=DAGSTER_HOME=<project-root>/orchestration/dagster_home
   # The four lines below are only needed for PostgreSQL run storage
   # (steps 2 and 3); omit them for the SQLite default.
   Environment=DAGSTER_PG_USER=...
   Environment=DAGSTER_PG_PASSWORD=...
   Environment=DAGSTER_PG_HOST=...
   Environment=DAGSTER_PG_DB=dagster
   ExecStart=<project-root>/.venv/bin/dagster-daemon run
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now cgdb-dagster-daemon
   ```

   If the previous setup ran a separate `dagster` UI process anywhere, remove it.

5. **Restart the process serving Django**, for example `sudo systemctl restart apache2` under Apache with mod_wsgi. A plain `git pull` is not enough, because mod_wsgi keeps the old code in memory until it restarts. The updated admin code submits runs through `dagster job launch` instead of the old `Popen` call.

6. **Smoke test:** start a maintenance job with the admin action "Trigger selected maintenance job(s)" and check that the `MaintenanceRun` changes from `running` to `success` or `failed` (through the run-status sensors in `orchestration/dagster_home/sensors.py`) and that `log` and `result_file` are filled. `journalctl -u cgdb-dagster-daemon -f` shows the daemon's activity live.
