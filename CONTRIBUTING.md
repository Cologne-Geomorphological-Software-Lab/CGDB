# CGDB Contributing Guide

## Welcome

Welcome to the CGDB (Cologne Geomorphological Database) Contributing Guide. CGDB is a research database for geomorphological and geoarchaeological data, developed at the Institute of Geography, University of Cologne.

Contributions we accept:

* **Bug reports**
  * Incorrect model behaviour or data-integrity issues
  * Admin interface regressions
  * Import/export failures
* **Feature development**
  * New analytical measurement types
  * Admin UX improvements
  * Orchestration pipelines
* **Tests**
  * Unit tests for model logic
  * Integration tests for admin views
* **Documentation**
  * Docstrings for non-obvious model methods
  * This guide and the README

At this time, we do not accept:

* Changes to the database schema without a corresponding migration and a discussion in the issue tracker
* New third-party dependencies without prior agreement
* Frontend JavaScript frameworks (the project uses django-unfold's built-in UI)

## Project overview

CGDB is a Django-based research database that stores field data (campaigns, locations, samples) and analytical results (luminescence dating, radiocarbon dating, grain size analysis, geochemistry, pollen) collected in the context of geomorphological and geoarchaeological research. Access control is managed at the project level via django-guardian.

The admin interface is the primary user-facing application. All measurement types are accessible exclusively through the Sample model at `/admin/field_data/sample/`.

## Ground rules

* Be respectful in all written communication — issues, pull requests, and commit messages.
* Open an issue before starting significant work so the approach can be agreed on.
* One logical change per pull request. Do not bundle unrelated fixes.
* All new behaviour must be covered by tests.

## Issue management

Issues are tracked in the GitHub issue tracker and follow a structured format:

* **BUG-XX** — a reproducible defect with a concrete failure scenario
* **FEAT-XX** — a clearly scoped feature request

When filing a bug:
1. State the expected and actual behaviour.
2. Name the affected file and line number if known.
3. Provide a minimal reproduction (model field values, URL, admin action).

When filing a feature request:
1. State the problem it solves, not just the desired solution.
2. Describe the proposed change at the level of model fields, admin classes, or URL routes.
3. Note any prerequisites (other features, migrations, new dependencies).

## Before you start

* Python 3.12 or 3.13
* PostgreSQL 15+ with PostGIS (for development), or SpatiaLite (for running tests only)
* OSGeo4W (Windows) or GDAL/GEOS system packages (Linux/macOS)
* Git

## Environment setup

1. Clone the repository and create a virtual environment:

   ```
   git clone <repo-url>
   cd CGDB
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # Linux/macOS
   pip install -r requirements.txt
   ```

2. Create `prototype/local_settings.py` with your database credentials, `SECRET_KEY`, `DEBUG = True`, and `ALLOWED_HOSTS`. Use `prototype/local_settings.example.py` as a template.

3. Apply migrations and create a superuser:

   ```
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. Run the development server:

   ```
   python manage.py runserver
   ```

### Troubleshoot

* **Windows — GDAL not found**: Install [OSGeo4W](https://trac.osgeo.org/osgeo4w/) and ensure `C:\OSGeo4W\bin` is on your `PATH`. `settings.py` configures the DLL paths automatically if OSGeo4W is installed at the default location.
* **SpatiaLite not found**: Required for tests only. Install via your system package manager (`libsqlite3-mod-spatialite` on Debian/Ubuntu).
* **`ModuleNotFoundError: No module named 'import_export'`**: Run `pip install -r requirements.txt` — some packages may not be installed in fresh environments.

## Best practices

* **No unnecessary comments.** Only add a comment when the *why* is non-obvious: a hidden constraint, a subtle invariant, or a workaround for a specific bug. Do not describe what the code does.
* **No speculative abstractions.** Three similar lines are better than a premature helper. Only generalise when there are three or more concrete call sites.
* **No broad exception handling.** Catch only the specific exception types that can actually occur. Never use `except Exception`.
* **Validate at system boundaries only.** Trust Django ORM guarantees and framework behaviour internally. Validate user input and data from external sources.
* **Admin changes must be tested.** Every new admin view, redirect, or form behaviour requires an integration test using the Django test client.

### Testing

**Where tests live**

Each app has a `tests/` subdirectory. Files are named after what they test:

```
field_data/tests/test_utils.py   # pure unit tests, no DB
field_data/tests/test_admin.py   # admin integration tests
analysis/tests/test_admin.py
```

**Which base class to use**

| Scenario | Base class |
|---|---|
| No database access needed | `django.test.SimpleTestCase` |
| Database access, each test isolated | `django.test.TestCase` |

Prefer `SimpleTestCase` for utility functions and pure model logic. Use `TestCase` for anything that touches the ORM or the admin.

**Shared fixtures**

Use `setUpTestData` (not `setUp`) to create database objects shared across tests in a class. Use `setUp` only for state that must be reset between tests (e.g. `client.force_login`).

```python
class _AdminSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser("admin", "a@test.com", "pw")
        cls.project = Project.objects.create(title="Test", label="T01", status="ACTIVE")
        ...

    def setUp(self):
        self.client.force_login(self.superuser)
```

Name shared base classes with a leading underscore (`_AdminSetup`) so pytest does not collect them as test suites.

**Admin integration tests**

Test admin views through the Django test client, not by calling view functions directly. Assert on HTTP status codes, context data, and redirects — not on rendered HTML strings.

```python
response = self.client.get(url)
self.assertEqual(response.status_code, 200)
self.assertEqual(response.context_data["cl"].params.get("sample__id__exact"), str(pk))
```

For redirect assertions, use `assertRedirects` with `fetch_redirect_response=False` so the test does not follow the redirect chain.

**What not to mock**

Do not mock the database. CGDB tests run against a real in-memory SpatiaLite database. Tests that mock ORM calls can pass while hiding real schema or query issues.

**Running the test suite**

```
python -m pytest
```

The `pytest.ini` at the repo root sets `DJANGO_SETTINGS_MODULE = prototype.test_settings`, which uses SpatiaLite and requires no external database. GeoDjango must be available on the system (see Environment setup).

To run a single file:

```
python -m pytest analysis/tests/test_admin.py -v
```

## Contribution workflow

### Branch creation

Branches follow the pattern `<type>/<short-description>`:

* `bug/fix-researcher-str` for bug fixes
* `feat/grain-size-classification` for features
* `test/sample-admin-coverage` for test-only changes
* `chore/remove-morphogrid` for cleanup

### Commit messages

Write commit messages in the imperative mood, present tense:

```
Fix GrainSizeAdmin redirect on POST

Add search_fields to RawMeasurementAdmin to enable autocomplete
```

* First line: 50 characters max, no trailing period.
* Optional body: explain *why*, not *what*. Reference issue numbers (`Closes BUG-05`).
* Do not amend published commits.

### Pull requests

* Open against `main`.
* Title mirrors the commit message style.
* Description must state: what changed, why, and how it was tested.
* Link the corresponding issue (`Closes #XX`).
* At least one approving review is required before merging.

### Code organisation

| App | Scope |
|---|---|
| `prototype` | Projects, researchers, permissions, dashboard |
| `field_data` | Campaigns, study areas, locations, samples |
| `analysis` | All measurement types and their admin |
| `bibliography` | Literature references |
| `laboratory` | Devices, methods, manufacturers |
| `orchestration` | Dagster pipelines, maintenance jobs |

The admin entry point for all measurements is `field_data/admin.py` (`SampleAdmin`). Measurement-specific admin classes live in `analysis/admin.py` and use `SampleContextMixin` to stay under the sample URL hierarchy. Do not add measurement models directly to the sidebar.

### Migrations

* Every model change must have a migration.
* Migrations must be reversible wherever possible.
* Do not squash migrations without prior agreement.
* Never edit a migration that has already been applied in production.

### Releases

There is no fixed release cadence. Deployments are triggered manually after review. Breaking schema changes are coordinated with the team lead before merging.
