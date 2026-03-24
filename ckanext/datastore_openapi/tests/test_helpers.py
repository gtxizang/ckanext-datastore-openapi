from unittest.mock import patch

from ckanext.datastore_openapi.helpers import (
    datastore_openapi_spec_url,
    datastore_openapi_dataset_spec_url,
    datastore_openapi_search_url,
    datastore_openapi_page_url,
    datastore_openapi_dataset_page_url,
)


class TestHelpers:
    @patch("ckanext.datastore_openapi.helpers.toolkit")
    def test_spec_url(self, mock_toolkit):
        mock_toolkit.url_for.return_value = "https://example.com/dataset/ds/resource/res/openapi.json"
        result = datastore_openapi_spec_url("res-1", "ds-1")
        mock_toolkit.url_for.assert_called_once_with(
            "datastore_openapi.resource_openapi_json",
            dataset_id="ds-1", resource_id="res-1",
            _external=True,
        )
        assert result == "https://example.com/dataset/ds/resource/res/openapi.json"

    @patch("ckanext.datastore_openapi.helpers.toolkit")
    def test_dataset_spec_url(self, mock_toolkit):
        mock_toolkit.url_for.return_value = "https://example.com/dataset/ds/openapi.json"
        result = datastore_openapi_dataset_spec_url("ds-1")
        mock_toolkit.url_for.assert_called_once_with(
            "datastore_openapi.dataset_openapi_json",
            dataset_id="ds-1",
            _external=True,
        )
        assert "openapi.json" in result

    @patch("ckanext.datastore_openapi.helpers.toolkit")
    def test_search_url(self, mock_toolkit):
        mock_toolkit.url_for.return_value = "/dataset/ds/resource/res/search"
        datastore_openapi_search_url("res-1", "ds-1")
        mock_toolkit.url_for.assert_called_once_with(
            "datastore_openapi.resource_search",
            dataset_id="ds-1", resource_id="res-1",
            _external=True,
        )

    @patch("ckanext.datastore_openapi.helpers.toolkit")
    def test_page_url(self, mock_toolkit):
        mock_toolkit.url_for.return_value = "/dataset/ds/resource/res/openapi"
        datastore_openapi_page_url("res-1", "ds-1")
        mock_toolkit.url_for.assert_called_once_with(
            "datastore_openapi.resource_swagger_ui",
            dataset_id="ds-1", resource_id="res-1",
            _external=True,
        )

    @patch("ckanext.datastore_openapi.helpers.toolkit")
    def test_dataset_page_url(self, mock_toolkit):
        mock_toolkit.url_for.return_value = "/dataset/ds/openapi"
        datastore_openapi_dataset_page_url("ds-1")
        mock_toolkit.url_for.assert_called_once_with(
            "datastore_openapi.dataset_swagger_ui",
            dataset_id="ds-1",
            _external=True,
        )
