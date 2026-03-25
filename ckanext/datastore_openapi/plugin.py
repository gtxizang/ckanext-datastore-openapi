import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from .actions import (
    datastore_openapi_resource_show,
    datastore_openapi_dataset_show,
    datastore_openapi_cache_invalidate,
)
from .auth import (
    datastore_openapi_resource_show as auth_resource_show,
    datastore_openapi_dataset_show as auth_dataset_show,
    datastore_openapi_cache_invalidate as auth_cache_invalidate,
)
from .blueprints import datastore_openapi
from .cache import invalidate_resource
from .dcat import inject_access_services
from .helpers import (
    datastore_openapi_spec_url,
    datastore_openapi_dataset_spec_url,
    datastore_openapi_search_url,
    datastore_openapi_page_url,
    datastore_openapi_dataset_page_url,
)


class DatastoreOpenapiPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, "templates")
        toolkit.add_public_directory(config, "public")

    # IActions

    def get_actions(self):
        return {
            "datastore_openapi_resource_show": datastore_openapi_resource_show,
            "datastore_openapi_dataset_show": datastore_openapi_dataset_show,
            "datastore_openapi_cache_invalidate": datastore_openapi_cache_invalidate,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            "datastore_openapi_resource_show": auth_resource_show,
            "datastore_openapi_dataset_show": auth_dataset_show,
            "datastore_openapi_cache_invalidate": auth_cache_invalidate,
        }

    # IBlueprint

    def get_blueprint(self):
        return [datastore_openapi]

    # IPackageController

    def after_dataset_show(self, context, pkg_dict):
        inject_access_services(pkg_dict)

    # IResourceController

    def after_resource_update(self, context, resource):
        res_id = resource.get("id") if isinstance(resource, dict) else None
        if res_id:
            invalidate_resource(str(res_id))

    def before_resource_delete(self, context, resource, resources):
        res_id = resource.get("id") if isinstance(resource, dict) else None
        if res_id:
            invalidate_resource(str(res_id))

    # ITemplateHelpers

    def get_helpers(self):
        return {
            "datastore_openapi_spec_url": datastore_openapi_spec_url,
            "datastore_openapi_dataset_spec_url": datastore_openapi_dataset_spec_url,
            "datastore_openapi_search_url": datastore_openapi_search_url,
            "datastore_openapi_page_url": datastore_openapi_page_url,
            "datastore_openapi_dataset_page_url": datastore_openapi_dataset_page_url,
        }
