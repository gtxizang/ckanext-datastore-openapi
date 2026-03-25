# ckanext-datastore-openapi

OpenAPI 3.1.0 spec generation for CKAN DataStore resources.

Every DataStore resource is already a queryable API — this extension generates OpenAPI specs from live metadata: column types become JSON Schema types, low-cardinality fields become enums, numeric fields get min/max ranges, and the data dictionary is embedded in the spec.

Introspection uses PostgreSQL's `pg_stats` catalog — a single query returns enum candidates, value distributions, and histogram bounds for all columns. Near-zero cost regardless of table size.

## Endpoints

| Endpoint | What it does |
|---|---|
| `GET /dataset/<dataset_id>/resource/<resource_id>/openapi.json` | OpenAPI 3.1.0 spec for a resource |
| `GET /dataset/<dataset_id>/openapi.json` | Combined spec for all DataStore resources in a dataset |
| `GET /dataset/<dataset_id>/resource/<resource_id>/search` | REST-style search proxy (datastore_search with resource_id in path) |
| `GET /dataset/<dataset_id>/resource/<resource_id>/openapi` | Swagger UI page for a resource |
| `GET /dataset/<dataset_id>/openapi` | Swagger UI page for a dataset |

Response schemas are fully typed:

```yaml
records:
  type: array
  items:
    type: object
    properties:
      bidding_zone: { type: string, enum: [SE1, SE2, SE3, SE4] }
      volume_mw: { type: number, format: double, minimum: 0.0, maximum: 9999.99 }
      timestamp: { type: string, format: date-time }
```

## How it works

1. **Introspect** — `datastore_search` with `limit=0` for field names/types and total count, then a single `pg_stats` query for enum detection (via `n_distinct` + `most_common_vals`) and range bounds (via `histogram_bounds`). For numeric/timestamp ranges, prefers `datastore_info` min/max when available (datapusher-plus), falling back to `pg_stats` histogram bounds.

2. **Build spec** — OpenAPI 3.1.0 with typed response schemas, enum filter parameters, and a data dictionary in `info.description`.

3. **Cache** — Per-resource specs cached via dogpile.cache (Redis or in-memory). Invalidated on resource update or delete, or manually via sysadmin action.

4. **DCAT** — Injects `access_services` into DataStore resources for `dcat:DataService` serialization via ckanext-dcat.

## Installation

```bash
git clone https://github.com/gtxizang/ckanext-datastore-openapi.git
cd ckanext-datastore-openapi
pip install .
```

Add to your CKAN config:

```ini
ckan.plugins = ... datastore_openapi ...
```

Requires CKAN 2.10+ and Python 3.9+.

## Configuration

All settings are optional — sensible defaults are provided.

```ini
# Fields to hide from specs (space-separated). Default: _id _full_text
# Fields starting with _ are also hidden automatically.
ckanext.datastore_openapi.hidden_fields = _id _full_text

# Cache backend. Default: dogpile.cache.memory
ckanext.datastore_openapi.cache.backend = dogpile.cache.redis
ckanext.datastore_openapi.cache.expiry = 3600
ckanext.datastore_openapi.cache.redis_url = redis://localhost:6379/1

# Max distinct values to treat as enum. Default: 25
ckanext.datastore_openapi.enum_threshold = 25

# Max fields to introspect per resource. Default: 50
ckanext.datastore_openapi.max_fields = 50

# Max resources in a dataset combined spec. Default: 20
ckanext.datastore_openapi.max_resources_per_dataset = 20

# DCAT DataService injection. Default: true
ckanext.datastore_openapi.dcat_enabled = true
```

## CKAN actions

| Action | Auth | Description |
|---|---|---|
| `datastore_openapi_resource_show` | Anonymous access allowed; visibility governed by `package_show` called internally | Returns OpenAPI spec for a resource |
| `datastore_openapi_dataset_show` | Anonymous access allowed; visibility governed by `package_show` called internally | Returns combined spec for a dataset |
| `datastore_openapi_cache_invalidate` | Sysadmin only | Invalidate cached specs |

## Swagger UI

Swagger UI 5.18.2 is vendored in the extension — no CDN dependency, no CSP issues.

## License

MIT
