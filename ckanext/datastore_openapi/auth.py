import ckan.plugins.toolkit as toolkit


@toolkit.auth_allow_anonymous_access
def datastore_openapi_resource_show(context, data_dict):
    return {"success": True}


@toolkit.auth_allow_anonymous_access
def datastore_openapi_dataset_show(context, data_dict):
    return {"success": True}


def datastore_openapi_cache_invalidate(context, data_dict):
    return {"success": False}
