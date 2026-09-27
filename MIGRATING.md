# Migrating

This guide lists the manual steps needed to upgrade an existing CGDB
deployment across a major version. Minor and patch releases need no steps
beyond `manage.py deploy` (see [Deploying updates](README.md#deploying-updates)).
What changed in each release is listed in [CHANGELOG.md](CHANGELOG.md).

Before any upgrade:

- Back up the database and the `media/` directory.
- Try the upgrade on a copy of the production database first.
- Run `manage.py deploy --dry-run` to review the steps the deploy command
  will take.

## Upgrading from 2.x to 3.0.0 "Iquique" (unreleased)

No steps yet. Every pull request that introduces a breaking change adds its
upgrade steps to this section.

## Upgrading from 1.x to 2.0.0

Work through the steps in order. Steps 5 to 7 concern the database and must
happen around `migrate`; `manage.py deploy` runs `migrate` in one go, so run
the first upgrade to 2.0.0 by hand.

### 1. Back up

Back up the database and `media/` as described above.

### 2. Python 3.13 and uv

CGDB 2.0.0 requires Python 3.13 or later. `requirements.txt` is gone;
dependencies are declared in `pyproject.toml` and locked in `uv.lock`.
Install [uv](https://docs.astral.sh/uv/) and replace
`pip install -r requirements.txt` with:

```bash
uv sync
```

### 3. Node.js and the frontend build

The map dashboard is built with Vite. Install Node.js and npm on the server,
then build the frontend and collect static files:

```bash
cd frontend
npm ci
npm run build
cd ..
uv run python manage.py collectstatic --noinput
```

`manage.py deploy` runs these steps on later updates.

### 4. Settings

Compare `prototype/local_settings.py` with
`prototype/local_settings_TEMPLATE.py`:

- Remove `DAGSTER_URL`; it is no longer used.
- With `DEBUG = False`, CGDB refuses to start unless `SECRET_KEY`,
  `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` and
  `SECURE_HSTS_SECONDS` are set to non-empty values. In 1.x, a
  `local_settings.py` that lacked one of the expected names was ignored
  entirely, with only a warning in the log.
- Optional: set `RASTER_CORPUS_ROOT` if raster files live somewhere other
  than `/corpus`.

### 5. Check for duplicates before migrating

Migrations `field_data.0012` and `field_data.0013` add uniqueness
constraints and fail if existing data violates them. List the offending
rows in `uv run python manage.py shell`:

```python
from django.db.models import Count
from field_data.models import Layer, StudyArea

print(StudyArea.objects.values("project", "label")
      .annotate(n=Count("id")).filter(n__gt=1))
print(Layer.objects.values("location", "identifier")
      .annotate(n=Count("id")).filter(n__gt=1))
```

Rename or merge the duplicates before continuing.

### 6. Migrate in two steps

`AccessoryParameter.method` changes from free text to a foreign key to
`Method`. Migration `laboratory.0007` matches the old text to method names
case-insensitively; rows without a match are left empty, and
`laboratory.0008` then drops the old text column. Stop in between to fix
those rows:

```bash
uv run python manage.py migrate laboratory 0007
```

```python
from laboratory.models import AccessoryParameter

for p in AccessoryParameter.objects.filter(method__isnull=True).exclude(method_legacy=""):
    print(p.pk, repr(p.method_legacy))
```

Assign the right `method` to each listed row (admin or shell), then run the
remaining migrations:

```bash
uv run python manage.py migrate
```

`migrate` also creates the predefined permission groups (Viewer,
Researcher, Principal Investigator and the domain groups).

### 7. Fill in project members

2.0.0 introduces `Project.members`. Members receive view, add and change
permission on the project automatically. The migration adds the field
empty, and the next time a project is saved in the admin, CGDB **removes**
view, add and change permission from every user who is not a member and
did not create the project. Fill in the members right after migrating, or
users silently lose access.

The snippet below makes every user who can currently change a project a
member of it, and lists users who can only view it. Membership would give
those users add and change permission too, so decide for each of them:
add them as members, or accept that they lose access on the next save and
grant it again through a permission group.

```python
from prototype.models import Project, ProjectUserObjectPermission

MEMBER_PERMS = ["view_project", "add_project", "change_project"]

for project in Project.objects.all():
    perms = ProjectUserObjectPermission.objects.filter(
        content_object=project, permission__codename__in=MEMBER_PERMS
    )
    editors = set(perms.filter(permission__codename="change_project")
                  .values_list("user", flat=True))
    viewers = set(perms.values_list("user", flat=True)) - editors
    project.members.add(*editors)
    if viewers:
        print(f"{project}: view-only users {sorted(viewers)}")
```

Then assign users to the new permission groups in the admin.

### 8. Dagster daemon

Maintenance jobs (backup, DuckDB export, integrity check) now run through a
persistent `dagster-daemon` instead of `dagster dev`. Replace the `dagster`
process in your Procfile or process manager with the daemon, set
`DAGSTER_HOME`, and install the systemd unit, following
[Updating an existing deployment to the daemon-based setup](README.md#updating-an-existing-deployment-to-the-daemon-based-setup).

### 9. Behaviour changes to be aware of

- Samples that have grain size, micro-XRF or generic measurements can no
  longer be deleted; delete the measurements first.
- Existing samples get the review status `draft`; existing luminescence and
  radiocarbon datings get `data_quality = pending`.
- `GenericMeasurement.MeasurementSeries` is now `measurement_series`.
  Scripts and import files that use the old name need updating; the
  database column is unchanged.
- Landform vector tiles on the map require PostgreSQL/PostGIS. On
  SpatiaLite the tile endpoint returns 501.

## Upgrading from 1.0 to 1.1

No manual steps. 1.1.0 is a minor release.
