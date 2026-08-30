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

## AI usage

> "In the kernel community we do open source because it results in
> better technology, not because of religious reasons. And so we make
> decisions primarily based on technical merit. Not fear of new tools."
>
> — Linus Torvalds, on AI-assisted contributions to the Linux kernel
> ([Ars Technica](https://arstechnica.com/ai/2026/07/linus-torvalds-to-critics-of-ai-coding-in-linux-fork-it-or-just-walk-away/), July 2026)

Using AI tools to help write code is allowed and welcomed. It does not
change any of the standards in this guide: judge the code on its merits,
not on how it was produced.

* **Verify by running the code, not by assuming it works.** Run the
  relevant tests, apply the migration, or exercise the admin action before
  calling something done — especially for measurement calculations, unit
  conversions, and import/export parsing. A plausible-looking value is not
  the same as a checked one.
* **Data-model and methodological choices are not the AI's to decide.**
  If a change has more than one defensible answer (which source takes
  precedence when two fields disagree, a unit conversion, how an
  ambiguous or partial import row should be handled), stop and ask before
  implementing it — open an issue for discussion (see *Ground rules*
  above) instead of picking one and hardcoding it.
* Every AI-generated change needs a human to actually read it before it
  is committed. Do not submit code you have not reviewed and understood
  yourself.
* AI-generated code follows the same rules as any other code, see *Best
  practices* below, especially "no speculative abstractions": prefer the
  simplest solution that solves the problem over a generated one that
  handles cases which cannot occur here.
* **AI is well-suited to writing and keeping docstrings up to date** —
  catching a docstring that's drifted from the model fields or behaviour
  it describes is exactly the kind of easy-to-neglect upkeep AI is good
  at. Use it for that. But it must produce this project's actual style
  (Google-style, per `pyproject.toml`'s `[tool.ruff.lint.pydocstyle]`),
  not generic filler.

  **What "AI slop" looks like** — reject a docstring like this on sight:

  ```python
  # BAD — filler opener, Attributes restates the field type Django's ORM
  # already declares, no information beyond the name.
  class RawMeasurement(BaseModel):
      """
      This model is used to store raw measurement data.

      Attributes:
          project (ForeignKey): The project.
          device (ForeignKey): The device used for measurement.
      """

  # GOOD — says what the field types can't: what "raw" means here.
  class RawMeasurement(BaseModel):
      """An uploaded measurement file before parsing into typed result rows."""
  ```

  Before committing a generated or edited docstring, re-read it and cut
  anything that fails this check:
  - Does the summary say something the model/field/method name doesn't
    already say?
  - Does every `Attributes:`/`Args:` line add meaning beyond the field's
    type?
  - Would deleting this sentence lose real information, or just make the
    docstring shorter?
* Install the pre-commit hooks (`uv run pre-commit install`). They run
  `ruff` (lint and format), `mypy`, `basedpyright`, `bandit`, `vulture`,
  `xenon`, and `pylint` (duplicate-code) before each commit — the same
  checks listed under *Tests* — and catch generated code that is
  needlessly complex, insecure, unused, duplicated, or fails
  linting/type checks before it ever reaches a pull request.

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
   uv sync
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
* **Data reconciliation and conversion choices belong in the open, not buried in a commit.** When a change has more than one defensible answer — which source takes precedence when two fields disagree (e.g. a stored corpus path vs. an uploaded file), a unit conversion, how a partial or ambiguous import row is handled — discuss it in the issue tracker first, and land it as an explicit, documented choice rather than an implicit one.

## Coding style

* **Type hints everywhere, clean under `mypy`.** `mypy` runs in `strict` mode here (`pyproject.toml`'s `[tool.mypy]`). Every function parameter and return type, and every field whose type isn't obvious from the assignment. Modern syntax only: `list[float]`, `X | None` — not `typing.List` or `typing.Optional`.

  The pre-commit `basedpyright` hook checks the whole project (`scripts/run-basedpyright.cmd`). The `mypy` hook is still scoped to `field_data/admin.py` and `field_data/models.py` (see `scripts/run-mypy.cmd`) — 6 of 8 first-party apps sit under a blanket `ignore_errors = true` mypy override (`pyproject.toml`'s `[[tool.mypy.overrides]]`), a separate, larger piece of tech debt. Hold new and touched code to strict typing manually where mypy doesn't yet enforce it.
* **`from __future__ import annotations`** at the top of every module.
* **Google-style docstrings**, consistent with *Best practices*' "no unnecessary comments" above — most private helpers and simple `__str__` overrides need none.
* `ruff check .` and `ruff format --check .` must both pass clean. Line length is 79 columns (`pyproject.toml`'s `[tool.ruff]`).

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

Also expected to stay clean on any touched code (the pre-commit hooks run all of these, plus basic file hygiene — trailing whitespace, merge-conflict markers, and private-key detection — see `.pre-commit-config.yaml`):

```
ruff check --fix
ruff format
mypy                 # scoped to field_data/admin.py, field_data/models.py — see scripts/run-mypy.cmd
basedpyright         # whole project — see scripts/run-basedpyright.cmd
bandit -c pyproject.toml -r <apps>          # security — see scripts/run-bandit.cmd
vulture <apps> vulture_whitelist.py --min-confidence 80   # dead code — see scripts/run-vulture.cmd
xenon --max-absolute B --max-modules B --max-average A    # complexity gate — see scripts/run-xenon.cmd
pylint <apps>        # duplicate-code only (pyproject.toml's [tool.pylint]) — see scripts/run-pylint-duplicate.cmd
```

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
