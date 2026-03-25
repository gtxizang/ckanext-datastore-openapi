# Review Response — ckanext-datastore-openapi

Response to Eric's code review of ckanext-openapi-view (2026-03-24). Rather than refactoring the original extension, this is a clean build addressing all feedback.

## Accountability Table

| # | Feedback | Status | How Addressed |
|---|----------|--------|---------------|
| 1 | `ckanext-name-view` is by convention a resource view plugin; `ckanext-openapiview` already in SVK | Done | Renamed to `ckanext-datastore-openapi` throughout |
| 2 | `api/action/` hierarchy has a specific shape, this isn't that. Prefer `[resource_url]/openapi.json` | Done | Routes: `/dataset/<dataset_id>/resource/<resource_id>/openapi.json`, `/search`, `/openapi` |
| 3 | Introspect looks expensive | Done | Single `pg_stats` query (0.137ms) replaces per-field SELECT DISTINCT (420ms/field) |
| 4 | Joel's `datastore_info` saves in DB rather than as cache | Done | `datastore_info` checked first, pg_stats as fallback |
| 5 | Cache invalidation tricky with timeseries; schema only changes on `datastore_create`, min/max changes anytime | Partial | See [Cache design notes](#cache-design-notes) below |
| 6 | "Is that `datastore_upsert`?" re: cache invalidation | Done | Removed `after_dataset_update`. Invalidation on `after_resource_update` which fires on `datastore_upsert`/`datastore_create` |
| 7 | Remove `-e` from pip install | Done | `pip install .` in README |
| 8 | `resource_show` auth == `dataset_show` unless overridden | Done | Auth stubs return `{"success": True}`, real auth via `package_show` in action layer |
| 9 | What's the license on `deepIntrospect`? | Done | Function rewritten from scratch as `introspect()`. No external dependency. Repo is MIT |
| 10 | Blanket includes for helpers/actions | Done | All imports explicit, zero wildcards |
| 11 | Not-found or permission error should return 404 | Done | Every route catches `(ObjectNotFound, NotAuthorized)` and returns 404. No 403 path |
| 12 | Vendor swagger-ui, not CDN | Done | Swagger UI 5.18.2 bundled in `public/vendor/swagger-ui/`. Zero CDN references |
| 13 | Context of none does the right thing | Done | `_context()` returns `{}`. No manual user/model/session construction |
| 14 | Use `url_for` not string construction | Done | `url_for` in all helpers and blueprints. Zero string construction |
| 15 | UUID regex matches aren't necessary | Done | No UUID regex. IDs passed directly to `package_show` |
| 16 | CSP with `unsafe-inline` is basically worthless | Done | No inline `<script>`. Spec URL via `data-spec-url` attribute, all JS from vendored external files |
| 17 | `package_show` and get resource from `package['resources']` | Done | `package_show` called, resource found by iterating `dataset["resources"]` |
| 18 | Don't write your own SQL quoting routines | Done | No SQL quoting. Only parameterised `pg_stats` query via SQLAlchemy `text()` |
| 19 | `WHERE foo IS NOT NULL` is a noop on aggregates; skip min/max, one query for enums | Done | Old SQL removed entirely. Single pg_stats query, `histogram_bounds` for ranges |
| 20 | Hidden fields: `_full_text`, anything starting with `_` | Done | Explicit set `{"_id", "_full_text"}` plus `startswith("_")` filter |
| 21 | Template: `res.datastore_active` not helper call | Done | All 3 templates use `res.datastore_active` |
| 22 | Never call with `ignore_auth=True` | Done | Zero matches for `ignore_auth` across entire codebase |

## Cache design notes

The cache invalidation concern around timeseries data deserves a fuller response.

**What we do:** Single per-resource cache with a configurable TTL (default 3600s), invalidated on `after_resource_update` which covers `datastore_upsert` and `datastore_create`.

**Schema vs stats:** Eric noted that schema only changes on `datastore_create` while min/max changes on every push. That's a real distinction we haven't separated into different cache keys. For the schema side (field names, types, enum candidates) the current approach is more than sufficient — it only goes stale if someone calls `datastore_create` and the cache hasn't expired yet, and the invalidation hook catches that anyway.

**Timeseries staleness:** For min/max on continuously-pushed timeseries, the stats will be at most `cache.expiry` seconds stale. However, the `histogram_bounds` from pg_stats themselves only update when PostgreSQL runs ANALYZE. Autoanalyze triggers after roughly `autovacuum_analyze_threshold + (autovacuum_analyze_scale_factor * table_size)` rows have changed — defaults are 50 rows + 10% of table size. For a 1.5M row table, that means autoanalyze won't fire until ~150,000 rows are inserted. So for large tables with small continuous pushes, pg_stats already lags behind the actual data regardless of our cache layer.

**datastore_info precedence:** When `datastore_info` is populated (Joel's datapusher-plus path), those min/max values take precedence over pg_stats and are as fresh as the last push.

**Open question:** We could split schema and stats into separate cache keys with different TTLs, but given that pg_stats itself isn't real-time for the values we're reading, it's not clear this adds meaningful freshness. Open to Eric's view on whether this needs tightening or whether the TTL approach is pragmatic enough for SVK's use case.
