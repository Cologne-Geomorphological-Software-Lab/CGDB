# Try the demo

With Docker installed, one command starts CGDB with a PostGIS database and synthetic data. No local Python, GDAL or Node setup is needed. Run it in a clone of the repository:

```bash
docker compose -f compose.demo.yml up
```

The first start builds the image and takes a few minutes. Then open <http://localhost:8000> and log in:

| Account | Password | Role |
|---|---|---|
| `demo_pi` | `demo` | Principal Investigator: can view and edit the demo project |
| `demo_viewer` | `demo` | Viewer: can only view it |

The demo project has a fictional study area with 8 locations, 24 samples and grain size, luminescence, radiocarbon, pollen and geochemistry data. The map at `/map/` shows the locations, the study area, a transect and, when the landform layer is switched on, six rectangular landform regions. The API documentation is at `/api/v1/schema/swagger-ui/`. All data is invented, including the landform regions.

Maintenance runs (backup, DuckDB export, integrity check) are open to superusers only. To try them, create one:

```bash
docker compose -f compose.demo.yml exec web python manage.py createsuperuser
```

## Not a production setup

The demo runs Django's development server with `DEBUG` on, the accounts have a known password, and the port is bound to `127.0.0.1` only. Use another password with `CGDB_DEMO_PASSWORD=... docker compose -f compose.demo.yml up`. The base maps, the place search and the optional WMS overlays load from external servers and need internet access.

## Stopping and resetting

Stopping and starting keeps the data. To remove the containers and all data:

```bash
docker compose -f compose.demo.yml down -v
```

To run the same checks as CI against a running demo: `bash docker/smoke_test.sh`. Outside Docker, `python manage.py load_demo_data` loads the same data into a development database. It refuses to run unless `DEBUG` is on, and `--reset` recreates the data.
