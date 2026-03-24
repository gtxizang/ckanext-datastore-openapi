from unittest.mock import patch, MagicMock

import pytest

from ckanext.datastore_openapi.actions import (
    _get_introspect_config,
    datastore_openapi_resource_show,
    datastore_openapi_dataset_show,
    datastore_openapi_cache_invalidate,
)


_CONFIG_DEFAULTS = {
    "ckanext.datastore_openapi.hidden_fields": "_id _full_text",
    "ckanext.datastore_openapi.enum_threshold": 25,
    "ckanext.datastore_openapi.max_fields": 50,
    "ckanext.datastore_openapi.max_resources_per_dataset": 20,
    "ckan.site_url": "https://data.example.com",
}


def _setup_toolkit(mock_toolkit):
    mock_toolkit.get_or_bust.side_effect = lambda d, k: d[k]
    mock_toolkit.ObjectNotFound = type("ObjectNotFound", (Exception,), {})
    mock_toolkit.NotAuthorized = type("NotAuthorized", (Exception,), {})
    mock_toolkit.ValidationError = type("ValidationError", (Exception,), {"error_dict": {}})
    mock_toolkit.config.get.side_effect = lambda key, default=None: _CONFIG_DEFAULTS.get(key, default)


class TestGetIntrospectConfig:
    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_defaults(self, mock_toolkit):
        mock_toolkit.config.get.side_effect = lambda key, default=None: {
            "ckanext.datastore_openapi.hidden_fields": "_id _full_text",
            "ckanext.datastore_openapi.enum_threshold": 25,
            "ckanext.datastore_openapi.max_fields": 50,
        }.get(key, default)

        config = _get_introspect_config()
        assert config["hidden_fields"] == {"_id", "_full_text"}
        assert config["enum_threshold"] == 25
        assert config["max_fields"] == 50

    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_custom_hidden_fields(self, mock_toolkit):
        mock_toolkit.config.get.side_effect = lambda key, default=None: {
            "ckanext.datastore_openapi.hidden_fields": "_id _full_text internal_col",
            "ckanext.datastore_openapi.enum_threshold": 25,
            "ckanext.datastore_openapi.max_fields": 50,
        }.get(key, default)

        config = _get_introspect_config()
        assert config["hidden_fields"] == {"_id", "_full_text", "internal_col"}


class TestResourceShow:
    @patch("ckanext.datastore_openapi.actions.set_cached")
    @patch("ckanext.datastore_openapi.actions.get_cached")
    @patch("ckanext.datastore_openapi.actions.introspect")
    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_calls_check_access(self, mock_toolkit, mock_introspect, mock_get, mock_set):
        _setup_toolkit(mock_toolkit)
        mock_toolkit.get_action.return_value = MagicMock(return_value={
            "id": "ds-001", "name": "test", "title": "Test",
            "resources": [{"id": "res-001", "name": "R1"}],
        })
        from dogpile.cache.api import NO_VALUE
        mock_get.return_value = NO_VALUE
        mock_introspect.return_value = {"fields": [], "totalRecords": 0, "sampleRecords": []}
        mock_toolkit.url_for.return_value = "/dataset/ds-001/resource/res-001/search"

        datastore_openapi_resource_show(
            {}, {"resource_id": "res-001", "dataset_id": "ds-001"}
        )

        mock_toolkit.check_access.assert_called_once_with(
            "datastore_openapi_resource_show", {}, {"resource_id": "res-001", "dataset_id": "ds-001"}
        )

    @patch("ckanext.datastore_openapi.actions.get_cached")
    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_returns_cached_spec(self, mock_toolkit, mock_get):
        _setup_toolkit(mock_toolkit)
        mock_toolkit.get_action.return_value = MagicMock(return_value={
            "id": "ds-001", "resources": [{"id": "res-001", "name": "R1"}],
        })
        cached_spec = {"openapi": "3.1.0", "paths": {}}
        mock_get.return_value = cached_spec

        result = datastore_openapi_resource_show(
            {}, {"resource_id": "res-001", "dataset_id": "ds-001"}
        )
        assert result == cached_spec

    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_raises_not_found_for_missing_resource(self, mock_toolkit):
        _setup_toolkit(mock_toolkit)
        mock_toolkit.get_action.return_value = MagicMock(return_value={
            "id": "ds-001", "resources": [{"id": "other-res", "name": "Other"}],
        })

        with pytest.raises(mock_toolkit.ObjectNotFound):
            datastore_openapi_resource_show(
                {}, {"resource_id": "res-missing", "dataset_id": "ds-001"}
            )

    @patch("ckanext.datastore_openapi.actions.set_cached")
    @patch("ckanext.datastore_openapi.actions.get_cached")
    @patch("ckanext.datastore_openapi.actions.introspect")
    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_raises_not_found_when_not_in_datastore(self, mock_toolkit, mock_introspect, mock_get, mock_set):
        _setup_toolkit(mock_toolkit)
        mock_toolkit.get_action.return_value = MagicMock(return_value={
            "id": "ds-001", "resources": [{"id": "res-001", "name": "R1"}],
        })
        from dogpile.cache.api import NO_VALUE
        mock_get.return_value = NO_VALUE
        mock_introspect.return_value = None

        with pytest.raises(mock_toolkit.ObjectNotFound):
            datastore_openapi_resource_show(
                {}, {"resource_id": "res-001", "dataset_id": "ds-001"}
            )

    @patch("ckanext.datastore_openapi.actions.set_cached")
    @patch("ckanext.datastore_openapi.actions.get_cached")
    @patch("ckanext.datastore_openapi.actions.introspect")
    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_generates_url_for_search(self, mock_toolkit, mock_introspect, mock_get, mock_set):
        _setup_toolkit(mock_toolkit)
        mock_toolkit.get_action.return_value = MagicMock(return_value={
            "id": "ds-001", "name": "test", "title": "Test",
            "resources": [{"id": "res-001", "name": "R1"}],
        })
        from dogpile.cache.api import NO_VALUE
        mock_get.return_value = NO_VALUE
        mock_introspect.return_value = {"fields": [], "totalRecords": 0, "sampleRecords": []}
        mock_toolkit.url_for.return_value = "/dataset/ds-001/resource/res-001/search"

        datastore_openapi_resource_show(
            {}, {"resource_id": "res-001", "dataset_id": "ds-001"}
        )

        mock_toolkit.url_for.assert_called_with(
            "datastore_openapi.resource_search",
            dataset_id="ds-001", resource_id="res-001",
        )


class TestDatasetShow:
    @patch("ckanext.datastore_openapi.actions.set_cached")
    @patch("ckanext.datastore_openapi.actions.get_cached")
    @patch("ckanext.datastore_openapi.actions.introspect")
    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_filters_to_datastore_active(self, mock_toolkit, mock_introspect, mock_get, mock_set):
        _setup_toolkit(mock_toolkit)
        mock_toolkit.get_action.return_value = MagicMock(return_value={
            "id": "ds-001", "name": "test", "title": "Test",
            "resources": [
                {"id": "res-001", "name": "R1", "datastore_active": True},
                {"id": "res-002", "name": "R2", "datastore_active": False},
                {"id": "res-003", "name": "R3", "datastore_active": True},
            ],
        })
        from dogpile.cache.api import NO_VALUE
        mock_get.return_value = NO_VALUE
        mock_introspect.return_value = {"fields": [], "totalRecords": 0, "sampleRecords": []}
        mock_toolkit.url_for.return_value = "/search"

        datastore_openapi_dataset_show({}, {"dataset_id": "ds-001"})

        assert mock_introspect.call_count == 2

    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_raises_not_found_when_no_datastore_resources(self, mock_toolkit):
        _setup_toolkit(mock_toolkit)
        mock_toolkit.get_action.return_value = MagicMock(return_value={
            "id": "ds-001", "name": "test", "title": "Test",
            "resources": [
                {"id": "res-001", "name": "R1", "datastore_active": False},
            ],
        })
        with pytest.raises(mock_toolkit.ObjectNotFound):
            datastore_openapi_dataset_show({}, {"dataset_id": "ds-001"})


class TestCacheInvalidate:
    @patch("ckanext.datastore_openapi.actions.invalidate_resource")
    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_invalidates_resource(self, mock_toolkit, mock_invalidate):
        _setup_toolkit(mock_toolkit)
        result = datastore_openapi_cache_invalidate(
            {}, {"resource_id": "res-001"}
        )
        mock_invalidate.assert_called_once_with("res-001")
        assert "resource:res-001" in result["invalidated"]

    @patch("ckanext.datastore_openapi.actions.invalidate_resource")
    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_invalidates_dataset_resources(self, mock_toolkit, mock_invalidate):
        _setup_toolkit(mock_toolkit)
        mock_toolkit.get_action.return_value = MagicMock(return_value={
            "resources": [{"id": "res-a"}, {"id": "res-b"}],
        })
        result = datastore_openapi_cache_invalidate(
            {}, {"dataset_id": "ds-001"}
        )
        assert mock_invalidate.call_count == 2
        assert "dataset:ds-001" in result["invalidated"]

    @patch("ckanext.datastore_openapi.actions.toolkit")
    def test_raises_validation_error_without_ids(self, mock_toolkit):
        _setup_toolkit(mock_toolkit)
        with pytest.raises(mock_toolkit.ValidationError):
            datastore_openapi_cache_invalidate({}, {})
