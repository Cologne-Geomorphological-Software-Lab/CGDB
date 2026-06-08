The Cologne Geomorphological Database System (CGDB)  is a comprehensive information system for managing complex geoscientific research data. It is specifically designed to support small research projects that must adhere to strict data management requirements set by funding bodies but often lack the financial and human resources to do so. The framework supports the transformation of raw research data into scientific knowledge. It addresses critical challenges, such as the rapid increase in the volume, variety, and complexity of geoscientific datasets, data heterogeneity, spatial complexity, and the need to comply with the FAIR (Findable, Accessible, Interoperable, and Reusable) principles. The approach optimizes the research management process by enhancing scalability and enabling interdisciplinary integration. It is adaptable to evolving research requirements and supports various data types and methodological approaches, such as machine learning and deep learning, that place high demands on the data and their formats. 

![admin_samples](admin_samples.png)

## Technology Stack

CGDB is built with:
- **[Django 6.0](https://www.djangoproject.com/)** - Web framework and ORM
- **[Django Unfold](https://github.com/unfoldadmin/django-unfold)** - Modern admin interface
- **[Dagster](https://dagster.io/)** (optional) - Data orchestration and ETL pipelines

## Requirements

- Python 3.12+
- GeoDjango dependencies (GDAL, PROJ, GEOS)
- SpatiaLite or PostgreSQL/PostGIS

## Installation for local development
To set up the framework for local development, navigate to the desired folder and clone the repository.

```
git clone git@github.com:Cologne-Geomorphological-Software-Lab/CGDB.git
```

```
cd CGDB
```

Set up a virtual environment, activate it and install the project's dependencies:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a copy of prototype *local_settings_TEMPLATE.py* as *local_settings.py*:

```
cp prototype/local_settings_TEMPLATE.py prototype/local_settings.py
```

For local development, edit local_settings.py with a text editor or an IDE according to the official Django documentation (especially Geodjango: https://docs.djangoproject.com/en/5.2/ref/contrib/gis/install/). It is advisable to use SpatialLite initially for development. Set DEBUG = True. Also, set STATIC_URL and MEDIA_URL to suitable values (for example, "/static/" and "/media/") as shown below:

```
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": "db.sqlite3",
    }
}
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
```

Install the geospatial libraries and SpatialLite:

```
sudo apt-get install binutils libproj-dev gdal-bin libsqlite3-mod-spatialite
```

Implement get_secret_key(). Only for local development you can allocate a static key to SECRET_KEY:

```
# WARNING: Do NOT use a static or hardcoded secret key in production!
# Generate a cryptographically secure, random value and NEVER commit real secrets to version control.
# For development only, you can use a placeholder, but be sure to change this for deployment.
def get_secret_key():
    return "!! REPLACE WITH A SECURE RANDOM SECRET KEY !!"

SECRET_KEY = get_secret_key()
```

Migrate the database and create a super user:
```
python manage.py migrate
python manage.py createsuperuser
```

Start the local development server:
```
python manage.py runserver
```

## Running the Tests

The test suite uses **pytest** with **pytest-django** and an in-memory SpatiaLite database — no PostgreSQL/PostGIS installation required.

### Prerequisites

#### Linux / macOS
Install the geospatial system libraries (same as for development):

```bash
sudo apt-get install binutils libproj-dev gdal-bin libsqlite3-mod-spatialite   # Debian/Ubuntu
brew install gdal proj spatialite-tools                                          # macOS
```

#### Windows
Install [OSGeo4W](https://trac.osgeo.org/osgeo4w/) (Network Installer → Express Install → GDAL). The default install path is `C:\OSGeo4W`.

The `conftest.py` at the project root automatically registers the OSGeo4W DLL directory so that GeoDjango can load its C libraries. No manual environment setup is required.

If you installed OSGeo4W to a non-default path, adjust `SPATIALITE_LIBRARY_PATH` in `prototype/test_settings.py` and the paths in `conftest.py` accordingly.

### Test settings

Tests run against `prototype.test_settings`, which is already configured in `pytest.ini`. This settings module:
- Uses an **in-memory SpatiaLite database** (no migrations required against a real DB)
- Replaces the password hasher with MD5 to speed up user creation in fixtures
- Sets a static `SECRET_KEY` safe for test use only

### Running all tests

From the `CGDB/` directory (where `manage.py` lives):

```bash
pytest
```

### Useful options

```bash
# Run a specific app's tests
pytest prototype/tests/
pytest analysis/tests/

# Run a single test file
pytest analysis/tests/test_luminescence.py

# Run a single test class or method
pytest prototype/tests/test_views.py::StatDataStructureTest
pytest prototype/tests/test_views.py::StatDataStructureTest::test_project_count_reflects_db

# Show verbose output with test names
pytest -v

# Show output (print / logging) from passing tests as well
pytest -s

# Stop after the first failure
pytest -x

# Run only tests matching a keyword
pytest -k "grainsize"

# Measure test coverage (requires pytest-cov)
pytest --cov=. --cov-report=term-missing
```

### Test structure

| App | Location | What is tested |
|---|---|---|
| `prototype` | `prototype/tests/test_models.py` | `Researcher`, `ResearchGroup`, `Project`, `Country`, `Province` models |
| `prototype` | `prototype/tests/test_mixins.py` | All admin permission mixins (`ProjectBased`, `Nested`, `Hybrid`, `Guardian`, `CreatedUpdated`) |
| `prototype` | `prototype/tests/test_views.py` | `stat_data()`, `_build_monthly_performance()`, `dashboard_callback()` |
| `bibliography` | `bibliography/tests/test_models.py` | `Author`, `ReferenceKeyword`, `Reference` str, ordering, relations |
| `laboratory` | `laboratory/tests/test_models.py` | `Manufacturer`, `Device`, `Accessory`, `Method`, `Calibration`, `Firmware`, `AccessoryParameter` |
| `analysis` | `analysis/tests/test_luminescence.py` | `LuminescenceDating` str, validators, fields, FK protection |
| `analysis` | `analysis/tests/test_grainsize_fromfile.py` | `GrainSize.from_file()` parser (happy path, errors, integration) |
| `analysis` | `analysis/tests/test_other_models.py` | Remaining analysis models and `GrainSize.save()` reclassification |

### Troubleshooting

**`WinError 127` / DLL not found (Windows)**
OSGeo4W is not installed or not in the expected path. Verify that `C:\OSGeo4W\bin\mod_spatialite.dll` exists and adjust `conftest.py` and `prototype/test_settings.py` if needed.

**`django.db.utils.OperationalError: unable to open database file`**
The SpatiaLite module cannot be loaded. Ensure the system library is installed (Linux: `libsqlite3-mod-spatialite`; Windows: OSGeo4W).

**`ModuleNotFoundError: No module named 'pytest'`**
Activate the virtual environment first: `source .venv/bin/activate` (Linux/macOS) or `.venv\Scripts\activate` (Windows).

---

## Data Orchestration (Optional)

CGDB includes an optional data orchestration module that provides a boilerplate for implementing data pipelines with [Dagster](https://dagster.io/). This enables data ingestion, ETL processes, data quality checks, integration with OLAP systems like DuckDB or whole analysis pipelines.

The orchestration layer is designed as a **starting point** that can be customised for your specific IT environment. 

**To enable:**

1. Uncomment Dagster dependencies in `requirements.txt` and install:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure Dagster URL in `prototype/local_settings.py`:
   ```python
   DAGSTER_URL = "http://localhost:3000"
   ```

3. Set Dagster home directory:
   ```bash
   export DAGSTER_HOME=$(pwd)/orchestration/dagster_home
   ```

4. Start both servers with honcho:
   ```bash
   honcho start
   ```
   - Django: `http://localhost:8000`
   - Dagster: `http://localhost:3000`

   Or start services individually:
   ```bash
   honcho start web      # Django only
   honcho start dagster  # Dagster only
   ```

The module is intentionally minimal to avoid overhead while providing a complete reference implementation for FAIR-compliant data management workflows.


![admin_luminescence](admin_luminescence.png)
## References

> Handy, D., Van der Meij, W. M., Zickel, M., and Reimann, T.: A database-driven research data framework for integrating and processing high-dimensional geoscientific data, EGUsphere [preprint], https://doi.org/10.5194/egusphere-2025-4832, 2025.

**Framework Dependencies:**
- Django - [https://www.djangoproject.com/](https://www.djangoproject.com/)
- Django Unfold - [https://github.com/unfoldadmin/django-unfold](https://github.com/unfoldadmin/django-unfold)
- Dagster - [https://dagster.io/](https://dagster.io/)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Citation

If you use CGDB in your research, please cite:

```
Handy, D., & van der Meij, M. (2025). Cologne-Geomorphological-Software-Lab/CGDB: intitial (v1.0.0). Zenodo. https://doi.org/10.5281/zenodo.17869731

```

## Security & Production Notes

**This is a research data framework.** Production deployment requires at least:

1. **Configure `local_settings.py` properly:**
   - Set strong SECRET_KEY (use environment variable)
   - Configure ALLOWED_HOSTS for your domain
   - Set DEBUG=False in production
   - Configure secure database credentials

2. **Production Server:**
   - Use Gunicorn/uWSGI (not Django runserver)
   - Configure reverse proxy (nginx/Apache)
   - Set up SSL/TLS certificates

3. **Additional Security:**
   - Implement rate limiting
   - Set up monitoring and logging
   - Regular security updates
   - Database backups

4. **Separation of OLTP & Data Orchestration:**
   - For production workloads, consider running Dagster on a separate server
   - Use read replicas or separate OLAP databases for analytics workloads
   - Avoid running heavy ETL jobs during peak operational hours

See Django deployment checklist: 
https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
