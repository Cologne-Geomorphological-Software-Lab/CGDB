# Deployment

CGDB is a research data framework. A production deployment needs at least the following.

## Settings

Configure `prototype/local_settings.py`:

- Set a strong `SECRET_KEY`, for example from an environment variable.
- Set `ALLOWED_HOSTS` to your domain.
- Set `DEBUG = False`. CGDB then refuses to start unless `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` and `SECURE_HSTS_SECONDS` are set, so it has to be served over HTTPS.
- Use separate, strong database credentials.

## Server

- Serve Django with a WSGI server such as Gunicorn, uWSGI or Apache with mod_wsgi, not with `runserver`.
- Put a reverse proxy (nginx or Apache) in front of it, with TLS certificates.
- Keep uploads and backups out of every directory the web server serves; see [Protected files](protected-files.md).
- Assign every staff user a role group; see [Roles and projects](roles-and-projects.md).

## Security and operation

- The REST API is rate-limited (`REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`). The counters live in the database cache, so they hold across all server processes.
- Set up monitoring and logging.
- Apply security updates regularly.
- Back up the database regularly. The backup maintenance job does this on demand; see [Data orchestration](orchestration.md).
- For heavy analytical workloads, consider running Dagster on a separate server, using read replicas or a separate OLAP database, and avoiding heavy jobs during peak hours.

See also Django's [deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/).

(deploying-updates)=
## Deploying updates

`python manage.py deploy` needs `sudo` (it backs up the database and restarts services) and covers everything **after** getting the new code onto the server. `git pull` is a separate, manual step first, run as yourself with your own git credentials, so `root` never needs git access of its own:

```bash
git pull --ff-only
sudo python manage.py deploy
```

`manage.py deploy` runs, in order:

1. a clean-working-tree check
2. a database backup before migrating (SQLite copy or `pg_dump`, whichever is active)
3. `uv sync`
4. `npm ci && npm run build`, which compiles the map dashboard's frontend to `static/dist/` and exits (see [Frontend](../getting-started/installation.md#frontend-map-dashboard))
5. `migrate`
6. `move_protected_media`, which moves uploads and backups left under `MEDIA_ROOT` by versions before 2.0.2 (see [Protected files](protected-files.md))
7. `collectstatic`
8. a restart of both services, followed by a check that each is `active` afterwards, not only that the restart command succeeded

On a failed migration, the error message names the backup's path so you can decide whether to restore it; nothing is rolled back automatically. Before the confirmation prompt, the command lists staff users without a role group, who can't see any project data (see [Roles and projects](roles-and-projects.md)).

The command needs a person at the keyboard: it asks for confirmation (skip with `--yes`), and no cron job, webhook or CI step starts it. `--dry-run` prints every step without executing anything, for example to review it before the first real run on a server. The implementation is in `prototype/management/commands/deploy.py`.
