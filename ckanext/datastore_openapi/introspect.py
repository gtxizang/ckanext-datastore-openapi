import logging
import re

from sqlalchemy import text

import ckan.plugins.toolkit as toolkit

from .type_map import TEXT_TYPES, RANGE_TYPES

log = logging.getLogger(__name__)

_PG_ARRAY_RE = re.compile(r"^\{(.*)\}$")


def _parse_pg_array(val):
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return list(val)
    m = _PG_ARRAY_RE.match(str(val))
    if not m:
        return []
    inner = m.group(1)
    if not inner:
        return []
    # Handle quoted elements: {"foo bar","baz"}
    result = []
    i = 0
    while i < len(inner):
        if inner[i] == '"':
            # Quoted element
            i += 1
            elem = []
            while i < len(inner):
                if inner[i] == '\\' and i + 1 < len(inner):
                    elem.append(inner[i + 1])
                    i += 2
                elif inner[i] == '"':
                    i += 1
                    break
                else:
                    elem.append(inner[i])
                    i += 1
            result.append("".join(elem))
        else:
            # Unquoted element — read until comma
            j = inner.index(",", i) if "," in inner[i:] else len(inner)
            val_str = inner[i:j].strip()
            if val_str.upper() == "NULL":
                result.append(None)
            else:
                result.append(val_str)
            i = j
        if i < len(inner) and inner[i] == ",":
            i += 1
    return [v for v in result if v is not None]


_engine = None


def _get_datastore_engine():
    global _engine
    if _engine is not None:
        return _engine
    from ckan.common import config
    read_url = config.get("ckan.datastore.read_url")
    if not read_url:
        read_url = config.get("ckan.datastore.write_url")
    if not read_url:
        return None
    from sqlalchemy import create_engine
    _engine = create_engine(read_url, pool_pre_ping=True)
    return _engine


def _query_pg_stats(engine, resource_id):
    sql = text(
        "SELECT attname, n_distinct, most_common_vals, histogram_bounds "
        "FROM pg_stats WHERE tablename = :table_name"
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"table_name": resource_id}).fetchall()
    stats = {}
    for row in rows:
        attname = row[0]
        stats[attname] = {
            "n_distinct": row[1],
            "most_common_vals": _parse_pg_array(row[2]),
            "histogram_bounds": _parse_pg_array(row[3]),
        }
    return stats


def _is_hidden(field_id, hidden_fields):
    if field_id in hidden_fields:
        return True
    return field_id.startswith("_")


def introspect(resource_id, context=None, config=None):
    if context is None:
        context = {}
    if config is None:
        config = {}

    hidden_fields = config.get("hidden_fields", {"_id", "_full_text"})
    enum_threshold = config.get("enum_threshold", 25)
    max_fields = config.get("max_fields", 50)

    try:
        meta = toolkit.get_action("datastore_search")(
            dict(context), {"resource_id": resource_id, "limit": 0}
        )
    except Exception:
        log.warning("Failed to fetch metadata for %s", resource_id, exc_info=True)
        return None

    if not meta or "fields" not in meta:
        return None

    try:
        sample = toolkit.get_action("datastore_search")(
            dict(context), {"resource_id": resource_id, "limit": 5}
        )
    except Exception:
        sample = {"records": []}

    all_fields = meta["fields"][:max_fields]
    total_records = meta.get("total", 0)
    sample_records = sample.get("records", [])

    ds_info = None
    try:
        ds_info = toolkit.get_action("datastore_info")(
            dict(context), {"id": resource_id}
        )
    except Exception:
        log.debug("datastore_info not available for %s", resource_id)

    info_stats = {}
    if ds_info and "fields" in ds_info:
        for fi in ds_info["fields"]:
            info_stats[fi["id"]] = fi

    pg_stats = {}
    if not info_stats:
        engine = _get_datastore_engine()
        if engine is not None:
            try:
                pg_stats = _query_pg_stats(engine, resource_id)
            except Exception:
                log.warning("pg_stats query failed for %s", resource_id, exc_info=True)

    enriched_fields = []
    for f in all_fields:
        fid = f["id"]
        enriched: dict = {
            "id": fid,
            "type": f["type"],
            "sample": sample_records[0].get(fid) if sample_records else None,
            "samples": [r[fid] for r in sample_records if r.get(fid) is not None],
        }
        if "info" in f:
            enriched["info"] = f["info"]

        if _is_hidden(fid, hidden_fields):
            enriched_fields.append(enriched)
            continue

        fi = info_stats.get(fid, {})
        ps = pg_stats.get(fid, {})

        if f["type"] in TEXT_TYPES:
            n_distinct = ps.get("n_distinct")
            mcv = ps.get("most_common_vals", [])

            if n_distinct is not None and 0 < n_distinct <= enum_threshold and mcv:
                enriched["isEnum"] = True
                enriched["enumValues"] = mcv
                enriched["distinctCount"] = int(n_distinct)
            elif n_distinct is not None:
                enriched["isEnum"] = False
                if n_distinct > 0:
                    enriched["distinctCount"] = int(n_distinct)

        if f["type"] in RANGE_TYPES:
            fi_min = fi.get("min")
            fi_max = fi.get("max")
            if fi_min is not None and fi_max is not None:
                enriched["min"] = fi_min
                enriched["max"] = fi_max
            else:
                bounds = ps.get("histogram_bounds", [])
                if bounds:
                    enriched["min"] = bounds[0]
                    enriched["max"] = bounds[-1]

        enriched_fields.append(enriched)

    return {
        "fields": enriched_fields,
        "totalRecords": total_records,
        "sampleRecords": sample_records,
    }
