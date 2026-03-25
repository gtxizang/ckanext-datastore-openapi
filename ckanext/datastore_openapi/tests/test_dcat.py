from unittest.mock import patch

from ckanext.datastore_openapi.dcat import inject_access_services


class TestInjectAccessServices:
    @patch("ckanext.datastore_openapi.dcat.toolkit")
    def test_injects_service_for_datastore_resource(self, mock_toolkit):
        mock_toolkit.asbool.return_value = True
        mock_toolkit.config.get.return_value = "true"
        mock_toolkit.url_for.side_effect = lambda name, **kw: (
            f"/search/{kw.get('resource_id', '')}"
            if "search" in name
            else f"/spec/{kw.get('resource_id', '')}"
        )

        dataset = {
            "name": "test-ds",
            "resources": [
                {"id": "res-123", "name": "Energy Prices", "datastore_active": True},
                {"id": "res-456", "name": "Static PDF", "datastore_active": False},
            ],
        }

        inject_access_services(dataset)

        ds_res = dataset["resources"][0]
        assert len(ds_res["access_services"]) == 1
        svc = ds_res["access_services"][0]
        assert svc["title"] == "DataStore API for Energy Prices"
        assert "res-123" in svc["endpoint_url"]
        assert svc["conforms_to"] == "https://spec.openapis.org/oas/v3.1.0"

        static_res = dataset["resources"][1]
        assert "access_services" not in static_res

    @patch("ckanext.datastore_openapi.dcat.toolkit")
    def test_modifies_in_place(self, mock_toolkit):
        mock_toolkit.asbool.return_value = True
        mock_toolkit.config.get.return_value = "true"
        mock_toolkit.url_for.side_effect = lambda name, **kw: "/url"

        dataset = {
            "name": "test-ds",
            "resources": [
                {"id": "res-123", "name": "Test", "datastore_active": True},
            ],
        }

        inject_access_services(dataset)
        assert len(dataset["resources"][0]["access_services"]) == 1

    @patch("ckanext.datastore_openapi.dcat.toolkit")
    def test_no_duplicates_on_repeated_calls(self, mock_toolkit):
        mock_toolkit.asbool.return_value = True
        mock_toolkit.config.get.return_value = "true"
        mock_toolkit.url_for.side_effect = lambda name, **kw: f"/url/{kw.get('resource_id', '')}"

        dataset = {
            "name": "test-ds",
            "resources": [
                {"id": "res-123", "name": "Test", "datastore_active": True},
            ],
        }

        inject_access_services(dataset)
        inject_access_services(dataset)
        assert len(dataset["resources"][0]["access_services"]) == 1

    @patch("ckanext.datastore_openapi.dcat.toolkit")
    def test_disabled_via_config(self, mock_toolkit):
        mock_toolkit.asbool.return_value = False
        mock_toolkit.config.get.return_value = "false"

        dataset = {
            "resources": [
                {"id": "res-123", "name": "Test", "datastore_active": True},
            ],
        }

        inject_access_services(dataset)
        assert "access_services" not in dataset["resources"][0]

    @patch("ckanext.datastore_openapi.dcat.toolkit")
    def test_handles_no_request_context(self, mock_toolkit):
        mock_toolkit.asbool.return_value = True
        mock_toolkit.config.get.return_value = "true"
        mock_toolkit.url_for.side_effect = RuntimeError("No request context")

        dataset = {
            "resources": [
                {"id": "res-123", "name": "Test", "datastore_active": True},
            ],
        }

        inject_access_services(dataset)
        assert "access_services" not in dataset["resources"][0]

    @patch("ckanext.datastore_openapi.dcat.toolkit")
    def test_skips_dataset_with_no_datastore_resources(self, mock_toolkit):
        mock_toolkit.asbool.return_value = True
        mock_toolkit.config.get.return_value = "true"

        dataset = {
            "resources": [
                {"id": "res-123", "name": "Static", "datastore_active": False},
            ],
        }

        inject_access_services(dataset)
        assert "access_services" not in dataset["resources"][0]
