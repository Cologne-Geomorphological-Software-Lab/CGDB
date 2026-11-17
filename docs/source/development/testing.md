# Running the tests

The test suite uses pytest with pytest-django and an in-memory SpatiaLite database; no PostgreSQL or PostGIS installation is needed for most tests.

## Prerequisites

### Linux and macOS

Install the geospatial system libraries (the same as for development):

```bash
sudo apt-get install binutils libproj-dev gdal-bin libsqlite3-mod-spatialite   # Debian/Ubuntu
brew install gdal proj spatialite-tools                                          # macOS
```

### Windows

Install [OSGeo4W](https://trac.osgeo.org/osgeo4w/) (Network Installer → Express Install → GDAL). The default install path is `C:\OSGeo4W`.

The `conftest.py` at the project root registers the OSGeo4W DLL directory so that GeoDjango can load its C libraries, and `prototype/test_settings.py` points `SPATIALITE_LIBRARY_PATH` at `C:\OSGeo4W\bin\mod_spatialite.dll` when it exists. If you installed OSGeo4W elsewhere, adjust both. If tests fail with "Cannot find proj.db", check that the `PROJ_LIB` environment variable points to OSGeo4W's `share\proj`, not to another installation.

## Test settings

Tests run against `prototype.test_settings`, configured in `pytest.ini`. This settings module:

- uses an in-memory SpatiaLite database
- replaces the password hasher with MD5 to speed up user creation in fixtures
- sets a static `SECRET_KEY` for tests only

## Running the tests

From the directory with `manage.py`:

```bash
pytest
```

Useful options:

```bash
# One app's tests
pytest prototype/tests/
pytest analysis/tests/

# A single file, class or test
pytest analysis/tests/test_luminescence.py
pytest prototype/tests/test_views.py::StatDataStructureTest
pytest prototype/tests/test_views.py::StatDataStructureTest::test_project_count_reflects_db

# Verbose output, print/logging output, stop at the first failure
pytest -v
pytest -s
pytest -x

# Only tests matching a keyword
pytest -k "grainsize"

# Coverage (requires pytest-cov)
pytest --cov=. --cov-report=term-missing
```

`pytest --cov` fails below the coverage floor in `pyproject.toml` (`[tool.coverage.report] fail_under`). The floor is a ratchet: it was set to the measured value when it was introduced and is raised when coverage grows. Do not lower it to get a pull request green; add tests instead.

## Testing against PostGIS

Production runs PostGIS, not SpatiaLite. A few endpoints use GIS-specific SQL (raw queries, vendor-specific ORM functions) that can behave differently on the two backends. Tests for that code are marked `@pytest.mark.gis` and run against both backends. Some features, for example the landform vector tiles (`ST_AsMVT`), have no SpatiaLite equivalent; their tests are marked `@pytest.mark.postgis_only` and are left out of the default run.

Start a local PostGIS instance with the repository's `docker-compose.yml`:

```bash
docker compose up -d postgis
```

Then run the marked tests against it:

```bash
DJANGO_SETTINGS_MODULE=prototype.test_settings_postgis pytest -m "gis or postgis_only"
```

`prototype/test_settings_postgis.py` reads the connection from the environment variables `CGDB_TEST_PG_HOST`, `_PORT`, `_NAME`, `_USER` and `_PASSWORD`, which default to the compose service. On Windows, GeoDjango loads GDAL and GEOS at `django.setup()` whatever database is used, so the OSGeo4W setup above is needed for PostGIS tests too.

## Continuous integration

Three workflows in `.github/workflows/` run on GitHub Actions. All actions are pinned to commit hashes, and Dependabot (`.github/dependabot.yml`) keeps those pins, `uv.lock`, `frontend/package-lock.json` and the Dockerfile base images current with one grouped pull request per ecosystem and week.

`tests.yml` is the pull-request gate and runs on every push and pull request:

| Job | What it checks |
|---|---|
| `lint` | ruff, ruff format, `makemigrations --check` (a model change without its migration), mypy, basedpyright, bandit, xenon and zizmor (the workflows themselves). The last four mirror the pre-commit hooks in `scripts/`, so a commit made with `--no-verify` still has to pass them. |
| `spatialite` | The suite without `postgis_only` tests, on Python 3.13 and 3.14, with the coverage floor described above. The coverage report appears in the job summary, and `coverage.xml` is kept as an artifact for two weeks. |
| `postgis` | The `gis` and `postgis_only` tests against PostGIS 16. |
| `frontend` | `npm ci && npm run build`, so a broken Vite build is reported in a minute rather than after the Docker build. |
| `upgrade-path` | Checks out the latest release tag, lets its own code and lockfile create the schema (and the demo data, once a release ships `load_demo_data`), then switches to the commit under test and runs `migrate`, `move_protected_media`, `load_demo_data` and `docker/smoke_test.sh` against a running `runserver`. This is the check behind [MIGRATING.md](../reference/migrating.md). |

`demo-image.yml` builds and smoke-tests the Docker demo for pull requests that touch it, scans the image with Trivy (fixable CRITICAL and HIGH findings fail the job) and publishes it to GHCR on release tags.

`nightly.yml` runs against `main` every night and on demand, for the checks that are too slow or too noisy for every pull request: the whole suite against PostGIS (to find tests that depend on a backend without being marked), `pip-audit` and `npm audit` over the lockfiles, and an arm64 build of the demo image under QEMU.

`documentation.yml` builds this site with warnings as errors and publishes it on pushes to `main`.

CodeQL runs through GitHub's default setup, configured in the repository settings rather than in a workflow file.

## Test structure

| App | Location | What is tested |
|---|---|---|
| `prototype` | `prototype/tests/test_models.py` | `Researcher`, `ResearchGroup`, `Project`, `Country`, `Province` models, `BaseModel.save()` audit trail (`created_by`/`updated_by`) |
| `prototype` | `prototype/tests/test_mixins.py` | All admin permission mixins (`ProjectBased`, `Nested`, `Hybrid`, `Guardian`, `CreatedUpdated`) |
| `prototype` | `prototype/tests/test_views.py` | `stat_data()`, `_build_monthly_performance()`, `dashboard_callback()` |
| `prototype` | `prototype/tests/test_map_views.py` | `/map/` dashboard and the `LocationViewSet.map` GeoJSON action (structure, permission filtering, geometry exclusion) |
| `prototype` | `prototype/tests/test_api_permissions.py` | `IsProjectMember` and the `ProjectPathPermission` family (`SampleScoped`, `CountingScoped`, `MeasurementScoped`, `RawMeasurementScoped`) |
| `prototype` | `prototype/tests/test_middleware.py` | `CurrentUserMiddleware` thread-local request-user tracking |
| `prototype` | `prototype/tests/test_admin.py` | `ProjectAdmin` member sync through `prototype.access.sync_member_permissions()` |
| `prototype` | `prototype/tests/test_admin_project_scoping.py` | Regression tests for admin base-class MRO ordering across project-scoped admins |
| `prototype` | `prototype/tests/test_permission_groups.py` | `create_permission_groups()` |
| `prototype` | `prototype/tests/test_signals.py` | `assign_permissions_to_creator` post_save signal |
| `prototype` | `prototype/tests/test_deploy_command.py` | `deploy` management command (step order, `--dry-run`, `--yes`, dirty-tree abort, migration-failure and backup-path reporting, post-restart health checks) |
| `prototype` | `prototype/tests/test_load_demo_data.py` | `load_demo_data` command (idempotence, demo account permissions, `--reset`, refusal without `DEBUG`, demo landform tile on PostGIS) |
| `field_data` | `field_data/tests/test_models.py` | `Location`, `Sample`, `StudyArea`, `Transect`, and related models |
| `field_data` | `field_data/tests/test_api.py` | `StudyAreaViewSet.map`/`TransectViewSet.map` GeoJSON actions |
| `field_data` | `field_data/tests/test_admin.py` | `SampleAdmin`'s analysis sub-views |
| `field_data` | `field_data/tests/test_filters.py` | FilterSet definitions |
| `field_data` | `field_data/tests/test_forms.py` | Forms |
| `field_data` | `field_data/tests/test_utils.py` | Utility functions (no DB) |
| `field_data` | `field_data/tests/test_checks.py` | The startup check that PROJ can transform a UTM point to WGS 84 |
| `bibliography` | `bibliography/tests/test_models.py` | `Author`, `ReferenceKeyword`, `Reference` str, ordering, relations |
| `bibliography` | `bibliography/tests/test_api.py` | Read-only API for all 3 models; `Reference` visible without project membership (shared catalog) |
| `laboratory` | `laboratory/tests/test_models.py` | `Manufacturer`, `Device`, `Accessory`, `Method`, `Calibration`, `Firmware`, `AccessoryParameter` |
| `laboratory` | `laboratory/tests/test_api.py` | Read-only API for all 7 models (`IsAuthenticated` only, no project scoping) |
| `analysis` | `analysis/tests/test_luminescence.py` | `LuminescenceDating` str, validators, fields, FK protection |
| `analysis` | `analysis/tests/test_grainsize_fromfile.py` | `GrainSize.from_file()` parser (happy path, errors, integration) |
| `analysis` | `analysis/tests/test_grainsize.py` | `GrainSize._reclassify()` (unit tests, no DB) |
| `analysis` | `analysis/tests/test_mps_parser.py` | The `.mps` file parsing functions in `analysis/mps_parser.py` (no DB, no Django) |
| `analysis` | `analysis/tests/test_other_models.py` | `RadiocarbonDating`, `Counting`, `Pollen`, `PollenCount`, `GenericMeasurement`, and `GrainSize.save()` reclassification |
| `analysis` | `analysis/tests/test_models.py` | `Algorithm`, `RawMeasurement` |
| `analysis` | `analysis/tests/test_api.py` | Sample-scoped, catalog and nested-path permission patterns (`GrainSizeViewSet`, `AlgorithmViewSet`, `PollenCountViewSet`) |
| `analysis` | `analysis/tests/test_admin.py` | `SampleContextMixin` redirect logic in `analysis/admin.py` |
| `analysis` | `analysis/tests/test_forms.py` | Forms |
| `geodata` | `geodata/tests/test_models.py` | `Landform` model (str, geometry round-trip, ordering, spatial `__intersects` lookup) |
| `geodata` | `geodata/tests/test_api.py` | `LandformViewSet` (list/detail, bbox-filtered GeoJSON, `IsAuthenticated` only) |
| `geodata` | `geodata/tests/test_import_landforms.py` | `import_landforms` management command (batching, `--no-clear`, `--source`, malformed-geometry skip) |
| `raster_data` | `raster_data/tests/test_models.py` | `DataSource`, `RasterScene`, `RasterDataset` |
| `raster_data` | `raster_data/tests/test_api.py` | Read/write API and manifest action; `created_by`/`updated_by` set for API-created records through a real session login |
| `orchestration` | `orchestration/tests/test_models.py` | `MaintenanceRun`, `DuckDBTableConfig` |
| `orchestration` | `orchestration/tests/test_admin.py` | `MaintenanceRunAdmin` permissions and actions, `_submit_maintenance_run` (submission, a failed launch, a subprocess that never starts) |
| `orchestration` | `orchestration/tests/test_jobs.py` | The three Dagster maintenance jobs (`backup_job`, `duckdb_export_job`, `integrity_check_job`) and `_record_result_file` |
| `orchestration` | `orchestration/tests/test_sensors.py` | `_sync_maintenance_run` and the run-status sensors' `default_status` |
| `orchestration` | `orchestration/tests/test_management.py` | `run_maintenance_job` management command (manual fallback) |
| `orchestration` | `orchestration/tests/test_signals.py` | `DuckDBTableConfig` default-row seeding |
