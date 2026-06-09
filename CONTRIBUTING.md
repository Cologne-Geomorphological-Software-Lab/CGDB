# CGDB Contributing Guide

## Welcome

Welcome to the CGDB (Cologne Geomorphological Database) Contributing Guide. CGDB is a research database for geomorphological, geochronological and geoarchaeological data, developed in the Cologne Geomorphological Software Laboratory at the Institute of Geography, University of Cologne.

Contributions we accept:

* **Bug reports**
  * Incorrect model behaviour or data-integrity issues
  * Admin interface regressions
  * Import/export failures
* **Feature development**
  * Admin UX improvements
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

## Ground rules

* Be respectful in all written communication — issues, pull requests, and commit messages.
* Open an issue before starting significant work so the approach can be agreed on.
* One logical change per pull request. Do not bundle unrelated fixes.
* All new behaviour must be covered by tests.

## Issue management

Issues are tracked in the GitHub issue tracker and follow a structured format.

When filing a bug:
1. State the expected and actual behaviour.
2. Name the affected file and line number if known.
3. Provide a minimal reproduction (model field values, URL, admin action).

When filing a feature request:
1. State the problem it solves, not just the desired solution.
2. Describe the proposed change at the level of model fields, admin classes, or URL routes.
3. Note any prerequisites (other features, migrations, new dependencies).

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

2. Create `CGDB/prototype/local_settings.py` with your database credentials, `SECRET_KEY`, `DEBUG = True`, and `ALLOWED_HOSTS`. Use `prototype/local_settings.example.py` as a template.

3. Apply migrations and create a superuser:

   ```
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. Run the development server:

   ```
   python manage.py runserver
   ```

## Best practices

* **No unnecessary comments.** Only add a comment when the *why* is non-obvious: a hidden constraint, a subtle invariant, or a workaround for a specific bug. Do not describe what the code does.
* **No speculative abstractions.** Three similar lines are better than a premature helper. Only generalise when there are three or more concrete call sites.
* **No broad exception handling.** Catch only the specific exception types that can actually occur. Never use `except Exception`.
* **Validate at system boundaries only.** Trust Django ORM guarantees and framework behaviour internally. Validate user input and data from external sources.

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

### Tests

Run the test suite with:

```
python -m pytest
```

The test settings use an in-memory SpatiaLite database (`prototype/test_settings.py`) — no PostgreSQL/PostGIS installation is required for tests.

GeoDjango must be available on the system for the test suite to run. On Windows this requires OSGeo4W.

Pre-existing test failures unrelated to your change are acceptable — document them in the pull request description.

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
