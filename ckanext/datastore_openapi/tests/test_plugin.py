from unittest.mock import patch, MagicMock

from ckanext.datastore_openapi.plugin import DatastoreOpenapiPlugin


class TestPluginWiring:
    def test_get_actions_returns_all_actions(self):
        plugin = DatastoreOpenapiPlugin()
        actions = plugin.get_actions()
        assert "datastore_openapi_resource_show" in actions
        assert "datastore_openapi_dataset_show" in actions
        assert "datastore_openapi_cache_invalidate" in actions
        assert len(actions) == 3

    def test_get_auth_functions_returns_all(self):
        plugin = DatastoreOpenapiPlugin()
        auth = plugin.get_auth_functions()
        assert "datastore_openapi_resource_show" in auth
        assert "datastore_openapi_dataset_show" in auth
        assert "datastore_openapi_cache_invalidate" in auth
        assert len(auth) == 3

    def test_get_blueprint_returns_list(self):
        plugin = DatastoreOpenapiPlugin()
        blueprints = plugin.get_blueprint()
        assert isinstance(blueprints, list)
        assert len(blueprints) == 1

    def test_get_helpers_returns_all(self):
        plugin = DatastoreOpenapiPlugin()
        helpers = plugin.get_helpers()
        assert "datastore_openapi_spec_url" in helpers
        assert "datastore_openapi_dataset_spec_url" in helpers
        assert "datastore_openapi_search_url" in helpers
        assert "datastore_openapi_page_url" in helpers
        assert "datastore_openapi_dataset_page_url" in helpers
        assert len(helpers) == 5


class TestResourceHooks:
    @patch("ckanext.datastore_openapi.plugin.invalidate_resource")
    def test_after_resource_update_invalidates(self, mock_invalidate):
        plugin = DatastoreOpenapiPlugin()
        plugin.after_resource_update({}, {"id": "res-123", "name": "Test"})
        mock_invalidate.assert_called_once_with("res-123")

    @patch("ckanext.datastore_openapi.plugin.invalidate_resource")
    def test_after_resource_update_handles_non_dict(self, mock_invalidate):
        plugin = DatastoreOpenapiPlugin()
        plugin.after_resource_update({}, "not-a-dict")
        mock_invalidate.assert_not_called()

    @patch("ckanext.datastore_openapi.plugin.invalidate_resource")
    def test_before_resource_delete_invalidates(self, mock_invalidate):
        plugin = DatastoreOpenapiPlugin()
        plugin.before_resource_delete({}, {"id": "res-456"}, [])
        mock_invalidate.assert_called_once_with("res-456")

    @patch("ckanext.datastore_openapi.plugin.invalidate_resource")
    def test_before_resource_delete_handles_missing_id(self, mock_invalidate):
        plugin = DatastoreOpenapiPlugin()
        plugin.before_resource_delete({}, {}, [])
        mock_invalidate.assert_not_called()


class TestDatasetHooks:
    @patch("ckanext.datastore_openapi.plugin.inject_access_services")
    def test_after_dataset_show_calls_inject(self, mock_inject):
        mock_inject.return_value = {"injected": True}
        plugin = DatastoreOpenapiPlugin()
        result = plugin.after_dataset_show({}, {"id": "ds-001"})
        mock_inject.assert_called_once_with({"id": "ds-001"})
        assert result == {"injected": True}
