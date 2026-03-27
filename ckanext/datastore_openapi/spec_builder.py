import copy

from .type_map import pg_to_jsonschema

MAX_VALUE_LEN = 200


def _truncate(value, max_len=MAX_VALUE_LEN):
    if value is None:
        return ""
    s = str(value)
    return s[:max_len] + "\u2026" if len(s) > max_len else s


def build_resource_spec(site_url, dataset_name, resource_name,
                        introspection, search_url, hidden_fields=None):
    if hidden_fields is None:
        hidden_fields = ["_id", "_full_text"]

    all_fields = (introspection or {}).get("fields", [])
    total_records = (introspection or {}).get("totalRecords", 0)

    hidden_set = set(hidden_fields)
    user_fields = [
        f for f in all_fields
        if f["id"] not in hidden_set and not f["id"].startswith("_")
    ]
    field_names = [f["id"] for f in user_fields]
    enum_fields = [
        f for f in user_fields
        if f.get("isEnum") and f.get("enumValues") and len(f["enumValues"]) > 1
    ]

    total_str = f"{total_records:,}" if total_records else "0"
    info_desc = f"{total_str} records \u00b7 {len(user_fields)} fields"

    record_properties = {}
    for f in user_fields:
        prop = pg_to_jsonschema(f["type"])
        if f.get("isEnum") and f.get("enumValues"):
            prop["enum"] = [_truncate(v, MAX_VALUE_LEN) for v in f["enumValues"]]
        if f.get("min") is not None and prop.get("type") in ("number", "integer"):
            try:
                prop["minimum"] = float(f["min"]) if "." in str(f["min"]) else int(f["min"])
            except (ValueError, TypeError):
                pass
        if f.get("max") is not None and prop.get("type") in ("number", "integer"):
            try:
                prop["maximum"] = float(f["max"]) if "." in str(f["max"]) else int(f["max"])
            except (ValueError, TypeError):
                pass
        record_properties[f["id"]] = prop

    enum_filter_params = []
    for f in enum_fields:
        enum_filter_params.append({
            "name": f"filter_{f['id']}",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
                "enum": [_truncate(v, MAX_VALUE_LEN) for v in f["enumValues"]],
            },
            "description": f"Filter by {f['id']} ({len(f['enumValues'])} values)",
        })

    sort_desc = (
        f'Sort string. Fields: {", ".join(field_names)}. '
        f'e.g. "{field_names[0]} asc"'
        if field_names
        else 'e.g. "field_name asc"'
    )
    fields_desc = (
        f"Comma-separated fields to return. Available: {', '.join(field_names)}"
        if field_names
        else "Comma-separated field names to return"
    )

    return {
        "openapi": "3.1.0",
        "info": {
            "title": f"{dataset_name} \u2014 {resource_name}",
            "description": info_desc,
            "version": "1.0.0",
        },
        "servers": [{"url": site_url}],
        "tags": [{"name": resource_name}],
        "paths": {
            search_url: {
                "get": {
                    "tags": [resource_name],
                    "operationId": "resourceSearch",
                    "summary": f"Search {resource_name}",
                    "description": (
                        f"Query with filters, full-text search, sorting, "
                        f"and pagination. Total records: **{total_str}**"
                    ),
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Full-text search across all fields",
                        },
                        *enum_filter_params,
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "default": 10, "maximum": 32000},
                            "description": "Max rows to return (max 32,000)",
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "schema": {"type": "integer", "default": 0},
                            "description": "Number of rows to skip",
                        },
                        {
                            "name": "fields",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": fields_desc,
                        },
                        {
                            "name": "sort",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": sort_desc,
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/SearchResponse"},
                                },
                            },
                        },
                    },
                },
            },
        },
        "components": {
            "schemas": {
                "SearchResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "result": {
                            "type": "object",
                            "properties": {
                                "records": {
                                    "type": "array",
                                    "description": "Row objects",
                                    "items": {
                                        "type": "object",
                                        "properties": record_properties,
                                    } if record_properties else {
                                        "type": "object",
                                    },
                                },
                                "fields": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                    "description": "Field metadata",
                                },
                                "total": {"type": "integer"},
                                "limit": {"type": "integer"},
                                "offset": {"type": "integer"},
                                "_links": {"type": "object"},
                            },
                        },
                    },
                },
            },
        },
    }


def _rewrite_refs(obj, old_name, new_name):
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key == "$ref" and isinstance(val, str):
                obj[key] = val.replace(
                    f"#/components/schemas/{old_name}",
                    f"#/components/schemas/{new_name}",
                )
            else:
                _rewrite_refs(val, old_name, new_name)
    elif isinstance(obj, list):
        for item in obj:
            _rewrite_refs(item, old_name, new_name)


def build_dataset_spec(site_url, dataset_name, resource_specs):
    combined_paths = {}
    combined_schemas = {}
    tags = set()

    for _, spec in resource_specs:
        spec = copy.deepcopy(spec)
        for path, path_item in spec.get("paths", {}).items():
            res_id_suffix = path.rsplit("/", 2)[-2][:8] if "/resource/" in path else path[-8:]
            for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
                namespaced = f"{schema_name}_{res_id_suffix}"
                combined_schemas[namespaced] = schema
                _rewrite_refs(path_item, schema_name, namespaced)
            for method_obj in path_item.values():
                if isinstance(method_obj, dict) and "operationId" in method_obj:
                    method_obj["operationId"] = f"{method_obj['operationId']}_{res_id_suffix}"
            combined_paths[path] = path_item
        for tag in spec.get("tags", []):
            tags.add(tag["name"])

    return {
        "openapi": "3.1.0",
        "info": {
            "title": dataset_name,
            "description": f"Combined API for all DataStore resources in **{dataset_name}**",
            "version": "1.0.0",
        },
        "servers": [{"url": site_url}],
        "tags": [{"name": t} for t in sorted(tags)],
        "paths": combined_paths,
        "components": {"schemas": combined_schemas},
    }
