import ckan.plugins.toolkit as toolkit


def datastore_openapi_spec_url(resource_id, dataset_id):
    return toolkit.url_for(
        "datastore_openapi.resource_openapi_json",
        dataset_id=dataset_id, resource_id=resource_id,
        _external=True,
    )


def datastore_openapi_dataset_spec_url(dataset_id):
    return toolkit.url_for(
        "datastore_openapi.dataset_openapi_json",
        dataset_id=dataset_id,
        _external=True,
    )


def datastore_openapi_search_url(resource_id, dataset_id):
    return toolkit.url_for(
        "datastore_openapi.resource_search",
        dataset_id=dataset_id, resource_id=resource_id,
        _external=True,
    )


def datastore_openapi_page_url(resource_id, dataset_id):
    return toolkit.url_for(
        "datastore_openapi.resource_swagger_ui",
        dataset_id=dataset_id, resource_id=resource_id,
        _external=True,
    )


def datastore_openapi_dataset_page_url(dataset_id):
    return toolkit.url_for(
        "datastore_openapi.dataset_swagger_ui",
        dataset_id=dataset_id,
        _external=True,
    )
