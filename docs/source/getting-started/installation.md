# Installation for local development

## Technology stack

- [Django 6.0](https://www.djangoproject.com/) with GeoDjango: web framework, ORM and spatial data (field data, landforms, raster scenes)
- [Django Unfold](https://github.com/unfoldadmin/django-unfold): admin interface
- [Django REST Framework](https://www.django-rest-framework.org/): the REST API under `/api/v1/` (see [REST API](../reference/rest-api.md)), covering all apps including `geodata` (landforms) and `raster_data` (raster scenes and datasets)
- [Vite](https://vitejs.dev/): frontend build for the `/map/` dashboard (`frontend/`, see [Frontend](#frontend-map-dashboard) below)
- [DuckDB](https://duckdb.org/): export target for analysis
- [Dagster](https://dagster.io/) (optional): maintenance jobs and data pipelines, without a UI (see [Data orchestration](../operations/orchestration.md))
- [uv](https://docs.astral.sh/uv/): Python dependency management

## Requirements

- Python 3.13
- GeoDjango dependencies (GDAL, PROJ, GEOS)
- SpatiaLite or PostgreSQL/PostGIS
- Node.js and npm, to build the map dashboard's frontend. On a production server they are only needed as a build tool during `python manage.py deploy`; nothing Node-based keeps running afterwards.

## Setup

Clone the repository:

```bash
git clone git@github.com:Cologne-Geomorphological-Software-Lab/CGDB.git
cd CGDB
```

Set up a virtual environment, activate it, and install the dependencies with [uv](https://docs.astral.sh/uv/):

```bash
python3 -m venv .venv
source .venv/bin/activate
uv sync
```

Copy `prototype/local_settings_TEMPLATE.py` to `prototype/local_settings.py`:

```bash
cp prototype/local_settings_TEMPLATE.py prototype/local_settings.py
```

Edit `local_settings.py` following the Django documentation, especially the [GeoDjango installation guide](https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/). SpatiaLite is the simplest database to start with. Set `DEBUG = True`, and set `STATIC_URL` and `MEDIA_URL` to suitable values, for example:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": "db.sqlite3",
    }
}
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
```

Install the geospatial libraries and SpatiaLite:

```bash
sudo apt-get install binutils libproj-dev gdal-bin libsqlite3-mod-spatialite
```

Implement `get_secret_key()`. For local development only, you can use a static key:

```python
# WARNING: Do NOT use a static or hardcoded secret key in production!
# Generate a cryptographically secure, random value and NEVER commit real secrets to version control.
def get_secret_key():
    return "!! REPLACE WITH A SECURE RANDOM SECRET KEY !!"

SECRET_KEY = get_secret_key()
```

Migrate the database and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Start the development server:

```bash
python manage.py runserver
```

To fill the development database with the demo data, run `python manage.py load_demo_data` (see [Try the demo](demo.md)).

(frontend-map-dashboard)=
## Frontend (map dashboard)

The `/map/` dashboard's frontend is a Vite-built app under `frontend/`, not plain static files. In development, Django's templates load it from a Vite dev server rather than a built bundle.

Install the frontend dependencies once:

```bash
cd frontend
npm install
cd ..
```

`python manage.py runserver` then starts the Vite dev server automatically alongside Django (see `PrototypeConfig.ready()` and `prototype/vite_dev_server.py`); there is nothing else to run. If you skip `npm install`, `runserver` still starts, but prints a warning and leaves the map dashboard's script unavailable. In the browser this shows up as a cross-origin or module-load error pointing at `localhost:5173`, not as an obvious "connection refused".

In production, `VITE_DEV_MODE=false` (the default when `DEBUG=False`) skips the dev server and serves the built bundle instead. `python manage.py deploy` (see [Deploying updates](../operations/deployment.md#deploying-updates)) runs `npm ci && npm run build` as a one-shot step: it compiles to `static/dist/` and exits, the same way `uv sync` does. Node and npm only need to be installed on the server as a build tool, like GDAL and PostGIS.
