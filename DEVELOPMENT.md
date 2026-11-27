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

* Add every user-facing change to the `[Unreleased]` section of [CHANGELOG.md](CHANGELOG.md), with the PR or issue number.
* A breaking change also adds its upgrade steps to the next major version's section in [MIGRATING.md](MIGRATING.md).
* When tagging a release, rename `[Unreleased]` to the new version and date, and update `version` and `date-released` in [CITATION.cff](CITATION.cff).

### Versioning

CGDB follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Versions are tagged `vMAJOR.MINOR.PATCH` on `main`.

* **MAJOR:** a change that needs manual steps to upgrade an existing deployment. Examples: a migration that can fail on existing data or changes its meaning, a removed or renamed model field, API field or export column, a new required setting, service or build tool, a raised minimum Python version. Every major release has a section in [MIGRATING.md](MIGRATING.md).
* **MINOR:** new features and usability improvements that upgrade cleanly with `manage.py deploy`. Migrations only add to the schema.
* **PATCH:** bug fixes and dependency updates with no new features.

Each major release gets a codename: a Chilean regional capital, taken in order from north to south. The codename appears in the GitHub release title and in the version heading in [CHANGELOG.md](CHANGELOG.md). Minor and patch releases keep the codename of their major version.

| Version | Codename | | Version | Codename |
|---|---|---|---|---|
| 2.0.0 | Arica | | 10.0.0 | Chillán |
| 3.0.0 | Iquique | | 11.0.0 | Concepción |
| 4.0.0 | Antofagasta | | 12.0.0 | Temuco |
| 5.0.0 | Copiapó | | 13.0.0 | Valdivia |
| 6.0.0 | La Serena | | 14.0.0 | Puerto Montt |
| 7.0.0 | Valparaíso | | 15.0.0 | Coyhaique |
| 8.0.0 | Santiago | | 16.0.0 | Punta Arenas |
| 9.0.0 | Rancagua | | | |

Version 1 predates the scheme and has no codename.
