# REST API

CGDB exposes most research data through a REST API under `/api/v1/`, next to the Django admin. The interactive documentation (drf-spectacular with Swagger UI) at `/api/v1/schema/swagger-ui/` is the complete, current list of endpoints; this page is an overview.

## Authentication

Every endpoint needs authentication. Either method works:

- **Session (cookie):** when you are logged into the admin in the same browser, API requests from that browser work without a token.
- **Token:** `POST /api/v1/token-auth/` with username and password returns a token. Send it as `Authorization: Token <key>` from scripts, curl or other tools.

## Coverage by app

| App | Access | Notes |
|---|---|---|
| `field_data` | read-only, project-scoped | Locations, samples, campaigns, study areas, layers, transects, plus the GeoJSON `map` actions used by the `/map/` dashboard |
| `analysis` | read-only, project-scoped | All analytical models (luminescence, radiocarbon and cosmogenic dating, grain size, micro-XRF, pollen counts, generic measurements and more); scoping follows each model's path to its sample and project |
| `laboratory` | read-only, catalog | Devices, methods, manufacturers, accessories, calibration: a shared equipment catalog, not project-scoped |
| `bibliography` | read-only, catalog | Authors, keywords, references: a shared literature catalog, visible to any authenticated user |
| `geodata` | read-only, catalog | Murphy landform regions, with bbox-filtered GeoJSON and vector tiles for the map |
| `raster_data` | read and create | Raster scenes and datasets, with a manifest action; writing requires add permission on the target project |
| `orchestration` | admin only | No API; maintenance runs are managed in the admin |

Project-scoped endpoints return only data of projects the user may view, plus literature locations (`data_source="literature"`), which everyone can see. Superusers see everything. The API is rate-limited; see [Deployment](../operations/deployment.md#security-and-operation).
