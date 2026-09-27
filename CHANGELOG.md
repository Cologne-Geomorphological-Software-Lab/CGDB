# Changelog

All notable changes to CGDB are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
What counts as a major, minor or patch release, and how major releases are
named, is described under [Versioning](CONTRIBUTING.md#versioning).
Upgrade steps for major versions are in [MIGRATING.md](MIGRATING.md).

## [Unreleased]

### Added

- `CHANGELOG.md`, `MIGRATING.md` and `CITATION.cff` (#210).

### Changed

- Dependency updates: Django 6.0.7, Django REST Framework 3.18.1,
  djangorestframework-gis 1.3.0, Dagster 1.13.23 (#191, #192).
- Frontend build tool Vite 7 → 8; pre-commit-hooks v5 → v6 (#228).

### Fixed

- README: example systemd unit uses placeholders instead of
  deployment-specific paths and users (#189).
- Tests now match per-project `Campaign.label` uniqueness and the
  placeholder returned by `Researcher.__str__` for researchers without a
  user (#227).

## [2.0.0] - 2026-08-31 "Arica"

> **Breaking changes.** Dependency management moved from pip to uv,
> Node.js/npm is required to build the frontend, maintenance jobs need a
> running `dagster-daemon`, Python 3.13+ is required, and the permission
> system was rewritten. Follow [MIGRATING.md](MIGRATING.md#upgrading-from-1x-to-200)
> before upgrading an existing deployment.

### Added

- Project-based permission system: `Project.members` grant view, add and
  change access automatically; predefined academic and domain permission
  groups, created on `migrate` or with `manage.py create_permission_groups`;
  audit fields `granted_at` / `granted_by` on object permissions (#69, #85).
- Map dashboard at `/map/`, built with Vite and OpenLayers: location,
  study area and transect editors, landform vector tiles, WMS overlays,
  measuring, search, filters and a satellite basemap (#70, #124, #125,
  #143, #176, #179).
- REST API at `/api/v1/` with session and token authentication,
  throttling, an OpenAPI schema and Swagger UI; landform tiles as
  Mapbox Vector Tiles (PostGIS only) (#145, #183).
- `geodata` app with the `Landform` model (Murphy Landform Regions) and the
  `import_landforms` command (#145).
- `raster_data` app for data sources, raster scenes and datasets, with GDAL
  metadata extraction (#171).
- Database maintenance with Dagster: backup, DuckDB export and integrity
  check jobs, run history in the admin, and
  `manage.py run_maintenance_job` as a manual fallback (#88, #126, #127,
  #174).
- `manage.py deploy` for guided server updates, with `--dry-run` and
  `--yes` (#174, #180, #181).
- `CosmogenicNuclideDating` model and admin (#122).
- `data_quality` flag and `quality_note` on luminescence and radiocarbon
  dating (#184).
- Review status on samples: draft, reviewed, accepted, rejected,
  archived (#100).
- `FieldPhoto` model with project-scoped downloads (#92).
- Location GPS accuracy, positioning method and location type; location
  import (#132, #133, #141).
- Grain size: `gravel` and `source` fields, all measurements of a sample
  shown in the sample admin, `.mps` file parser (#114, #174).
- Import/export for lookup tables, analysis and bibliography models; bulk
  tag actions; Munsell colour help on layers (#96, #98, #101, #103).
- `modified_at` timestamp on all models.
- Test suite (SpatiaLite and PostGIS), GitHub Actions CI, Sphinx
  documentation, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` and
  a pull request template.

### Changed

- Dependencies are managed with uv (`pyproject.toml`, `uv.lock`);
  Python 3.13+ is required (#128, #129, #130).
- Dagster runs as a headless `dagster-daemon` instead of `dagster dev`;
  `DAGSTER_HOME` sets the run storage location (#185, #188).
- django-unfold ≥ 0.99, django-guardian ≥ 3.3.2; new dependencies
  django-vite, drf-spectacular, djangorestframework-gis and pandas.
- With `DEBUG = False`, startup fails unless `SECRET_KEY`,
  `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` and
  `SECURE_HSTS_SECONDS` are set (#74).
- Uniqueness is now scoped: `Sample.identifier`, `Campaign.label` and
  `StudyArea.label` per project, `Layer.identifier` per location,
  `Tag.slug` only when set (#75, #79, #82).
- Samples with grain size, micro-XRF or generic measurements can no longer
  be deleted (`on_delete=RESTRICT`).
- `AccessoryParameter.method` is a foreign key to `Method` instead of free
  text.
- `GenericMeasurement.MeasurementSeries` renamed to `measurement_series`
  (the database column is unchanged).
- Object permissions are only stored for projects, researchers, research
  groups and references, no longer for every model.
- Revised admin interfaces for samples, locations, field data,
  luminescence and laboratory data.

### Removed

- `requirements.txt` (replaced by `pyproject.toml`).
- `DAGSTER_URL` setting and the Dagster sidebar link.
- The example Dagster assets and jobs shipped in 1.1.0.

### Fixed

- `Researcher.__str__` failed for researchers without a user (#71).
- Import/export resources referenced wrong or missing fields (#72, #73,
  #76, #142).
- Settings from `local_settings.py` were ignored when one name was
  missing (#74).
- Member permission changes were not atomic (#77).
- Project deadlines could precede the start date (#81).
- Location choices were not restricted to accessible projects (#87).
- Grain size autocomplete (#112), full-width changelists (#113),
  datetime handling, raster admin errors for non-superusers, Dagster backup
  and daemon failures (#185, #187, #188).

### Security

- Sample analysis views accepted analyses belonging to other samples
  (IDOR) (#121).
- Objects could be moved into projects without the required permission
  (IDOR) (#177).
- Bounding-box filter bypass in the API; field photos served only through
  a permission-checked view; API throttling and permission hardening
  (#183).
- Tag admin leaked data through the `Referer` header; case-insensitive
  upload extension check (#121).
- Frontend dependency vulnerability (nanoid) (#188).

## [1.1.0] - 2026-01-05

### Added

- Optional Dagster orchestration (`orchestration` app) with example assets
  and jobs.

### Changed

- Pinned versions in `requirements.txt`.
- Logging instead of `print` statements.

### Security

- Validation of uploaded grain size files: extension, size and integrity.
- Global upload limit of 100 MB (configurable).
- `SECRET_KEY`, SSL redirect and secure cookies are read from
  `local_settings.py`.

## [1.0.0] - 2025-12-09

Initial release, accompanying Handy et al. (2026),
<https://doi.org/10.5194/gi-15-165-2026>.

### Added

- Django/GeoDjango apps `prototype` (projects, researchers, research
  groups), `field_data` (study areas, sites, campaigns, locations, layers,
  samples), `analysis` (luminescence, radiocarbon, grain size, pollen,
  micro-XRF, generic and raw measurements), `bibliography` and
  `laboratory` (devices, methods, calibrations).
- Admin interface based on django-unfold, object-level permissions with
  django-guardian, import/export with django-import-export.

[Unreleased]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/releases/tag/v1.0.0
