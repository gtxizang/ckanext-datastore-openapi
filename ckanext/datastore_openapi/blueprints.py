import json

from flask import Blueprint, Response, request

import ckan.plugins.toolkit as toolkit

datastore_openapi = Blueprint("datastore_openapi", __name__)

VENDOR_BASE = "/vendor/swagger-ui"


def _json_response(data, status=200):
    body = {
        "help": "https://docs.ckan.org/en/latest/api/",
        "success": True,
        "result": data,
    }
    return Response(
        json.dumps(body, default=str),
        status=status,
        content_type="application/json; charset=utf-8",
    )


def _error_response(message, status=404):
    error_types = {400: "Validation Error", 404: "Not Found"}
    body = {
        "help": "https://docs.ckan.org/en/latest/api/",
        "success": False,
        "error": {"message": message, "__type": error_types.get(status, "Not Found")},
    }
    return Response(
        json.dumps(body),
        status=status,
        content_type="application/json; charset=utf-8",
    )


def _context():
    return {}


# --- JSON spec endpoints ---

@datastore_openapi.route(
    "/dataset/<dataset_id>/resource/<resource_id>/openapi.json",
    methods=["GET"],
)
def resource_openapi_json(dataset_id, resource_id):
    try:
        spec = toolkit.get_action("datastore_openapi_resource_show")(
            _context(), {"resource_id": resource_id, "dataset_id": dataset_id}
        )
        return Response(
            json.dumps(spec, default=str),
            status=200,
            content_type="application/json; charset=utf-8",
        )
    except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
        return _error_response("Not found", 404)


@datastore_openapi.route(
    "/dataset/<dataset_id>/openapi.json",
    methods=["GET"],
)
def dataset_openapi_json(dataset_id):
    try:
        spec = toolkit.get_action("datastore_openapi_dataset_show")(
            _context(), {"dataset_id": dataset_id}
        )
        return Response(
            json.dumps(spec, default=str),
            status=200,
            content_type="application/json; charset=utf-8",
        )
    except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
        return _error_response("Not found", 404)


# --- Search proxy ---

@datastore_openapi.route(
    "/dataset/<dataset_id>/resource/<resource_id>/search",
    methods=["GET"],
)
def resource_search(dataset_id, resource_id):
    try:
        ctx = _context()
        dataset = toolkit.get_action("package_show")(dict(ctx), {"id": dataset_id})
        if not any(r["id"] == resource_id for r in dataset.get("resources", [])):
            return _error_response("Not found", 404)

        data_dict: dict = {"resource_id": resource_id}

        for param in ("q", "fields", "sort", "records_format", "include_total", "distinct"):
            val = request.args.get(param)
            if val is not None:
                data_dict[param] = val

        for int_param, max_val in (("limit", 32000), ("offset", None)):
            raw = request.args.get(int_param)
            if raw is not None:
                try:
                    val = int(raw)
                except ValueError:
                    return _error_response(f"{int_param} must be an integer", 400)
                if val < 0:
                    return _error_response(f"{int_param} must not be negative", 400)
                if max_val is not None:
                    val = min(val, max_val)
                data_dict[int_param] = val

        filters = {}
        for key, val in request.args.items():
            if key.startswith("filter_") and val:
                filters[key[7:]] = val

        filters_json = request.args.get("filters")
        if filters_json:
            try:
                explicit = json.loads(filters_json)
                if isinstance(explicit, dict):
                    for k, v in explicit.items():
                        if isinstance(k, str) and isinstance(v, (str, list)):
                            filters[k] = v
            except (json.JSONDecodeError, TypeError):
                return _error_response("filters must be valid JSON", 400)

        if filters:
            data_dict["filters"] = filters

        result = toolkit.get_action("datastore_search")(dict(ctx), data_dict)
        return _json_response(result)
    except toolkit.ValidationError as e:
        return _error_response(str(e.error_dict) if hasattr(e, "error_dict") else str(e), 400)
    except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
        return _error_response("Not found", 404)


# --- Swagger UI pages ---

@datastore_openapi.route(
    "/dataset/<dataset_id>/resource/<resource_id>/openapi",
    methods=["GET"],
)
def resource_swagger_ui(dataset_id, resource_id):
    try:
        ctx = _context()
        dataset = toolkit.get_action("package_show")(dict(ctx), {"id": dataset_id})
        resource = None
        for r in dataset.get("resources", []):
            if r["id"] == resource_id:
                resource = r
                break
        if resource is None:
            return toolkit.abort(404)

        spec_url = toolkit.url_for(
            "datastore_openapi.resource_openapi_json",
            dataset_id=dataset_id, resource_id=resource_id,
            _external=True,
        )
        site_url = toolkit.config.get("ckan.site_url", "").rstrip("/")
        back_url = toolkit.url_for("dataset.read", id=dataset["name"])
        title = f"{dataset.get('title', dataset['name'])} \u2014 {resource.get('name', resource_id)}"

        return toolkit.render(
            "datastore_openapi/swagger_page.html",
            extra_vars={
                "title": title,
                "spec_url": spec_url,
                "site_url": site_url,
                "back_url": back_url,
                "vendor_base": VENDOR_BASE,
            },
        )
    except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
        return toolkit.abort(404)


@datastore_openapi.route(
    "/dataset/<dataset_id>/openapi",
    methods=["GET"],
)
def dataset_swagger_ui(dataset_id):
    try:
        ctx = _context()
        dataset = toolkit.get_action("package_show")(dict(ctx), {"id": dataset_id})

        spec_url = toolkit.url_for(
            "datastore_openapi.dataset_openapi_json",
            dataset_id=dataset_id,
            _external=True,
        )
        site_url = toolkit.config.get("ckan.site_url", "").rstrip("/")
        back_url = toolkit.url_for("dataset.read", id=dataset["name"])
        title = dataset.get("title", dataset["name"])

        return toolkit.render(
            "datastore_openapi/swagger_page.html",
            extra_vars={
                "title": title,
                "spec_url": spec_url,
                "site_url": site_url,
                "back_url": back_url,
                "vendor_base": VENDOR_BASE,
            },
        )
    except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
        return toolkit.abort(404)
