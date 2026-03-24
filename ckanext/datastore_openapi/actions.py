import logging

import ckan.plugins.toolkit as toolkit
from ckan.logic import side_effect_free
from dogpile.cache.api import NO_VALUE

from .cache import resource_cache_key, get_cached, set_cached, invalidate_resource
from .introspect import introspect
from .spec_builder import build_resource_spec, build_dataset_spec

log = logging.getLogger(__name__)

_DEFAULT_MAX_RESOURCES = 20


def _get_introspect_config():
    hidden_raw = toolkit.config.get(
        "ckanext.datastore_openapi.hidden_fields", "_id _full_text"
    )
    hidden_fields = set(s.strip() for s in hidden_raw.split() if s.strip())
    return {
        "hidden_fields": hidden_fields,
        "enum_threshold": int(
            toolkit.config.get("ckanext.datastore_openapi.enum_threshold", 25)
        ),
        "max_fields": int(
            toolkit.config.get("ckanext.datastore_openapi.max_fields", 50)
        ),
    }


def _get_site_url():
    url = toolkit.config.get("ckan.site_url", "").rstrip("/")
    if not url:
        log.warning("ckan.site_url not set")
    return url


def _resource_spec(resource_id, dataset, resource, context):
    cache_key = resource_cache_key(resource_id)
    cached = get_cached(cache_key)
    if cached is not NO_VALUE:
        return cached

    config = _get_introspect_config()
    introspection = introspect(
        resource_id, context=dict(context), config=config
    )
    if introspection is None:
        return None

    site_url = _get_site_url()
    dataset_id = dataset.get("id") or dataset.get("name")
    search_url = toolkit.url_for(
        "datastore_openapi.resource_search",
        dataset_id=dataset_id, resource_id=resource_id,
    )
    spec = build_resource_spec(
        site_url=site_url,
        dataset_name=dataset.get("title", dataset.get("name", "")),
        resource_name=resource.get("name") or resource.get("description", resource_id),
        introspection=introspection,
        search_url=search_url,
        hidden_fields=list(config["hidden_fields"]),
    )

    set_cached(cache_key, spec)
    return spec


@side_effect_free
def datastore_openapi_resource_show(context, data_dict):
    toolkit.check_access("datastore_openapi_resource_show", context, data_dict)
    resource_id = toolkit.get_or_bust(data_dict, "resource_id")
    dataset_id = toolkit.get_or_bust(data_dict, "dataset_id")

    dataset = toolkit.get_action("package_show")(dict(context), {"id": dataset_id})

    resource = None
    for r in dataset.get("resources", []):
        if r["id"] == resource_id:
            resource = r
            break

    if resource is None:
        raise toolkit.ObjectNotFound("Resource not found in dataset")

    spec = _resource_spec(resource_id, dataset, resource, context)
    if spec is None:
        raise toolkit.ObjectNotFound("Resource not in DataStore")
    return spec


@side_effect_free
def datastore_openapi_dataset_show(context, data_dict):
    toolkit.check_access("datastore_openapi_dataset_show", context, data_dict)
    dataset_id = toolkit.get_or_bust(data_dict, "dataset_id")

    dataset = toolkit.get_action("package_show")(dict(context), {"id": dataset_id})

    ds_resources = [
        r for r in dataset.get("resources", [])
        if r.get("datastore_active")
    ]

    max_resources = int(toolkit.config.get(
        "ckanext.datastore_openapi.max_resources_per_dataset",
        _DEFAULT_MAX_RESOURCES,
    ))
    if len(ds_resources) > max_resources:
        log.info(
            "Dataset %s: %d DataStore resources, capping at %d",
            dataset_id, len(ds_resources), max_resources,
        )
        ds_resources = ds_resources[:max_resources]

    resource_specs = []
    for res in ds_resources:
        try:
            spec = _resource_spec(res["id"], dataset, res, context)
            if spec:
                res_name = res.get("name") or res.get("description", res["id"])
                resource_specs.append((res_name, spec))
        except toolkit.NotAuthorized:
            pass
        except Exception:
            log.warning("Skipping resource %s", res["id"], exc_info=True)

    if not resource_specs:
        raise toolkit.ObjectNotFound("No accessible DataStore resources")

    site_url = _get_site_url()
    return build_dataset_spec(
        site_url=site_url,
        dataset_name=dataset.get("title", dataset["name"]),
        resource_specs=resource_specs,
    )


def datastore_openapi_cache_invalidate(context, data_dict):
    toolkit.check_access("datastore_openapi_cache_invalidate", context, data_dict)

    resource_id = data_dict.get("resource_id")
    dataset_id = data_dict.get("dataset_id")

    if not resource_id and not dataset_id:
        raise toolkit.ValidationError(
            {"resource_id": ["Provide resource_id or dataset_id"]}
        )

    invalidated = []
    if resource_id:
        invalidate_resource(resource_id)
        invalidated.append(f"resource:{resource_id}")
    if dataset_id:
        dataset = toolkit.get_action("package_show")(
            dict(context), {"id": dataset_id}
        )
        for res in dataset.get("resources", []):
            invalidate_resource(res["id"])
            invalidated.append(f"resource:{res['id']}")
        invalidated.append(f"dataset:{dataset_id}")

    return {"invalidated": invalidated}
