import logging

import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)


def inject_access_services(pkg_dict):
    """Modify pkg_dict in place — after_dataset_show ignores return values."""
    enabled = toolkit.asbool(
        toolkit.config.get("ckanext.datastore_openapi.dcat_enabled", "true")
    )
    if not enabled:
        return

    has_ds = any(
        r.get("datastore_active") for r in pkg_dict.get("resources", [])
    )
    if not has_ds:
        return

    try:
        toolkit.url_for("datastore_openapi.resource_search",
                        dataset_id="test", resource_id="test")
    except RuntimeError:
        return

    dataset_id = pkg_dict.get("name") or pkg_dict.get("id")

    for resource in pkg_dict.get("resources", []):
        if not resource.get("datastore_active"):
            continue

        resource_id = resource["id"]
        resource_name = (
            resource.get("name") or resource.get("description") or resource_id
        )

        search_url = toolkit.url_for(
            "datastore_openapi.resource_search",
            dataset_id=dataset_id, resource_id=resource_id,
            _external=True,
        )
        spec_url = toolkit.url_for(
            "datastore_openapi.resource_openapi_json",
            dataset_id=dataset_id, resource_id=resource_id,
            _external=True,
        )

        service = {
            "title": f"DataStore API for {resource_name}",
            "endpoint_url": search_url,
            "endpoint_description": spec_url,
            "conforms_to": "https://spec.openapis.org/oas/v3.1.0",
        }

        if "access_services" not in resource:
            resource["access_services"] = []

        existing_urls = {s.get("endpoint_url") for s in resource["access_services"]}
        if service["endpoint_url"] not in existing_urls:
            resource["access_services"].append(service)
