# Changelog

All notable changes to CGDB are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
What counts as a major, minor or patch release, and how major releases are
named, is described under [Versioning](https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/blob/main/CONTRIBUTING.md#versioning).
Upgrade steps for major versions are in [MIGRATING.md](https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/blob/main/MIGRATING.md).

## [Unreleased]

### Added

- A Docker demo: `docker compose -f compose.demo.yml up` starts CGDB with
  PostGIS, the Dagster daemon and synthetic data, without a local Python,
  GDAL or Node setup (#279). See "Try the demo" in the README. It runs with
  `DEBUG` on and a known password and is not meant for production. Release
  tags publish the image to GHCR for amd64.
- `manage.py load_demo_data` creates the demo project, the accounts
  `demo_pi` and `demo_viewer` and six landform regions. It can run
  repeatedly without duplicating data, `--reset` recreates everything, and
  it refuses to run unless `DEBUG` is on.
- Radiocarbon datings have an `age_error` field for the uncertainty the
  laboratory reports, in the same unit as `age`. It is optional, appears in
  the admin, the API, the table import and export, and existing datings
  keep an empty value. A date without its uncertainty could not be
  calibrated or published (#194).

### Changed

- The DuckDB export writes list and dict values (`GrainSize.classes`,
  `measured_data`) as JSON text and decimal values (`RadiocarbonDating.age`)
  as floats. Before, lists arrived as Python reprs such as `[0.04, 0.05]`
  and decimals as text, which no reader could parse without guesswork.
  `Pollen`, `PollenCount` and `Parameter` are exported as dimension tables,
  so pollen counts and the names of geochemistry parameters can be rebuilt
  from the file; existing installations receive the three table
  configurations on the next `migrate` (#284).
- The code that turns project membership into permissions moved from the
  project admin to `prototype.access.sync_member_permissions`, so other code
  can grant membership the same way. Behaviour is unchanged.
- The documentation moved from the README to a Sphinx site in `docs/`,
  written in Markdown (MyST): getting started, operations, development and a
  reference with the REST API, the data model of every app, this changelog
  and the migration guide. The README is now a short overview with links.
  `myst-parser` is a new dependency.

### Fixed

- The radiocarbon dating API now returns `data_quality` and `quality_note`,
  which the admin and the import already had (#283).
- "Save" on a measurement form shows the success message again and returns
  to the sample's tab for that analysis, where the new record is listed.
  Before, it landed on the sample's own tab with no message, as if nothing
  had been saved (#242).
- A `.$av` grain size upload that cannot be parsed is reported as an error
  on the file field and nothing is saved. Before, the admin answered with a
  server error and the form was lost. The file is now parsed while the form
  is validated and no longer passes through a temporary file (#241).
- A location whose coordinates PROJ cannot transform to WGS 84 is reported
  as an error on the coordinate fields instead of a server error. On
  Windows, the OSGeo4W setup now sets `PROJ_DATA` as well as `PROJ_LIB`, so
  a `PROJ_DATA` inherited from another program no longer breaks every
  transform, and a system check tries one UTM transform at startup (#249).
- The analysis tabs (Grain Size, Radiocarbon Dating and so on) appear only
  on pages that belong to one sample. On the sample add form they linked to
  the global measurement lists, and following one discarded the unsaved
  sample (#271).
- `settings.py` now serves the project's `static/` directory and stores
  uploads under `media/` by default, so a `local_settings.py` written after
  the installation guide no longer loses the logo and the stylesheet of the
  geometry widget, which left study areas, transects and landforms without
  a map to draw on (#253, #212). Production settings still override
  `STATIC_ROOT` and `MEDIA_ROOT`.
- The grain size fractions are labelled as what they are, the DIN EN ISO
  14688-1 classes (2 / 6.3 / 20 / 63 / 200 / 630 / 2000 µm), instead of
  "Wentworth". Values are unchanged (#193).
- A reference can be saved with a single author and without an abstract;
  "Second author" and "Abstract" are optional. The form rejects a lead
  author who is also listed as second author, the workaround the old rule
  forced. Existing references may carry that workaround: list them with
  `Reference.objects.filter(second_author=F("lead_author"))` (#243).
- Tags are optional on layers, as on locations and samples, and the layer
  form offers and accepts only tags of the layer content type. Before, a
  layer could not be saved without a tag, and tags made for samples were
  accepted (#251).
- A raw measurement only accepts samples of its own project; the error
  names the samples that belong elsewhere, and the change form offers only
  the project's samples. Existing records are not changed: list them with
  `RawMeasurement.objects.exclude(sample__project=F("project"))` (#244).
- A location identifier must be unique within its project, as the form
  always claimed. Until now only (campaign, identifier) was enforced, so
  locations without a campaign could share an identifier and references
  to it became ambiguous. The rule is validated on every save path, in the
  admin, the table import and scripts; the database constraint follows in
  3.0 (#256).
- A pollen counting accepts each taxon once; a second row for the same
  taxon is rejected in the admin and on save. The constraint and the
  decimal `number` field follow in 3.0 (#285).
- `manage.py check_duplicates` lists the locations and pollen counts that
  already violate these two rules, so they can be resolved before the
  upgrade to 3.0.
- A grain size distribution is checked before the fractions are computed
  from it, in the admin, the API and the table import: `classes` and
  `measured_data` must be lists of numbers of the same length, the classes
  positive and increasing, the values not negative and not all zero.
  Before, lists of different length were truncated silently while the
  percentages were still divided by the sum of the full list, so the
  stored fractions did not add up. One value per class remains the rule
  until #195 settles bin boundaries (#282).

## [2.0.2] - 2026-11-15 "Arica"

### Security

- Working with project data now needs both the permission from the user's
  role group and the permission on the project, in the admin, the REST API,
  table imports, photo downloads, landform tiles and the map dashboard.
  Before this, membership in a project was enough to edit its data, even for
  users in the "Viewer" group, who were also offered "Delete selected" in
  the admin (#245). Staff users without a role group lose access to project
  data: assign each of them "Viewer", "Researcher" or "Principal
  Investigator" before upgrading. `manage.py deploy` names these users
  before it asks for confirmation.
- The admin checked raw measurements against the project of their samples,
  which it could never reach, so only the role decided: a "Researcher" who
  could only view a project could change and delete its raw measurements.
  The admin now uses the measurement's own project, as the REST API does;
  the list shows raw measurements by that project.
- Uploaded files (field photos, raw and processed measurement data, analysis
  scripts, micro-XRF element maps, raster scenes) and maintenance results
  (database backups, DuckDB exports, integrity reports) are no longer stored
  under `MEDIA_ROOT`. Before this, a web server serving `/media/` handed them
  out without any login, including complete database backups under a
  guessable name. They now live under the new setting
  `PROTECTED_MEDIA_ROOT` (default: `protected_media/` in the project
  directory) and reach a browser only through `/files/`, which checks the
  role and project permission like the admin does; backups are for
  superusers only. Optionally, Apache (`X-Sendfile`) or nginx
  (`X-Accel-Redirect`) can send the files, see `PROTECTED_MEDIA_SERVER`.
  `manage.py deploy` moves existing files over with the new command
  `manage.py move_protected_media`, which never overwrites and stops on any
  conflicting file. `manage.py check --deploy` warns while protected files
  remain under `MEDIA_ROOT`.
- A transect's campaign must now belong to the project of its study area,
  in the admin and the REST API. Before this, the API accepted a campaign of
  any project, whose label the map then showed to users of the transect's
  project. Existing transects are not changed.
- The REST API's rate limits now hold across all web server processes. The
  cache that stores their counters was kept per process, so the login limit
  of 10 attempts per hour applied to each process separately and reset on
  every restart. The default cache is now a database table, created by
  `migrate`; a cache configured in `local_settings.py` takes precedence.
- The map's WMS proxy (`/api/wms-proxy`) no longer follows redirects, which
  could lead it away from the allowed host, and passes on only XML/GML
  answers up to 2 MB, marked `nosniff`. Before this, it relayed any content
  type, so an HTML answer would have run in the CGDB site's origin.

### Fixed

- The permission groups now cover cosmogenic nuclide dating, pollen
  counts, micro-XRF element maps, field photos, accessory parameters and
  raster data, with new domain groups "Cosmogenic Nuclides" and "Raster
  Data". Landforms can be viewed by every role. Before this, only
  superusers could open these records. Existing installations get the new
  permissions on the next `migrate` (#245).
- `pyproject.toml` declared version "1" instead of the release version. It
  now matches the release, and a test keeps `pyproject.toml`,
  `CITATION.cff` and this changelog on the same version (#209).
- Test runs no longer write uploaded files into the source tree.

## [2.0.1] - 2026-11-04 "Arica"

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

### Security

- Admin table imports now follow project permissions: they require the
  model's `add` permission, and each row is checked against the project.
  Staff users without a permission group lose import and export (#280).
- Bulk tag actions require change permission on each record and write to
  the admin log (#280).
- API tokens can be deleted in the admin; URLs use the user ID instead of
  the token key, and the bulk delete action was removed (#280).
- Dependency updates for known vulnerabilities: Django 6.0.10 (now capped
  below 6.1), Django REST Framework 3.18.3, Pillow 13.0.0, urllib3 2.8.0,
  certifi 2026.10.23, filelock 4.2.8, multidict 7.2.1, graphql-core 3.2.13,
  Vite 8.3.5, source-map-js 1.2.2; development tools pylint 4.1.3 and
  virtualenv 21.15.5 (#277).

## [2.0.0] - 2026-08-31 "Arica"

> **Breaking changes.** Dependency management moved from pip to uv,
> Node.js/npm is required to build the frontend, maintenance jobs need a
> running `dagster-daemon`, Python 3.13+ is required, and the permission
> system was rewritten. Follow [MIGRATING.md](https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/blob/main/MIGRATING.md#upgrading-from-1x-to-200)
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

[Unreleased]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/compare/v2.0.2...HEAD
[2.0.2]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/releases/tag/v1.0.0
