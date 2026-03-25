import copy

from ckanext.datastore_openapi.spec_builder import (
    build_resource_spec,
    build_dataset_spec,
    _truncate,
    _sanitise_for_table,
)

SEARCH_URL = "/dataset/ds-001/resource/res-001/search"


def _build(introspection, **kwargs):
    defaults = {
        "site_url": "https://data.example.com",
        "dataset_name": "Test Dataset",
        "resource_name": "Test Resource",
        "introspection": introspection,
        "search_url": SEARCH_URL,
    }
    defaults.update(kwargs)
    return build_resource_spec(**defaults)


class TestBuildResourceSpec:
    def test_produces_valid_openapi_structure(self, introspection_result):
        spec = _build(introspection_result, dataset_name="Energy Market Data",
                       resource_name="Hourly Prices")

        assert spec["openapi"] == "3.1.0"
        assert "Energy Market Data" in spec["info"]["title"]
        assert "Hourly Prices" in spec["info"]["title"]
        assert spec["servers"][0]["url"] == "https://data.example.com"

    def test_search_url_used_as_path(self, introspection_result):
        spec = _build(introspection_result)
        assert SEARCH_URL in spec["paths"]
        assert len(spec["paths"]) == 1

    def test_typed_response_schema(self, introspection_result):
        spec = _build(introspection_result)
        props = (
            spec["components"]["schemas"]["SearchResponse"]
            ["properties"]["result"]["properties"]["records"]
            ["items"]["properties"]
        )

        assert props["bidding_zone"]["type"] == "string"
        assert props["bidding_zone"]["enum"] == ["SE1", "SE2", "SE3", "SE4"]
        assert props["volume_mw"]["type"] == "number"
        assert props["volume_mw"]["format"] == "double"
        assert props["volume_mw"]["minimum"] == 0.0
        assert props["timestamp"]["type"] == "string"
        assert props["timestamp"]["format"] == "date-time"
        assert props["is_active"]["type"] == "boolean"
        assert props["tags"]["type"] == "array"

    def test_enum_filter_params(self, introspection_result):
        spec = _build(introspection_result)
        params = spec["paths"][SEARCH_URL]["get"]["parameters"]
        filter_params = [p for p in params if p["name"].startswith("filter_")]

        assert len(filter_params) == 1
        assert filter_params[0]["name"] == "filter_bidding_zone"
        assert filter_params[0]["schema"]["enum"] == ["SE1", "SE2", "SE3", "SE4"]

    def test_hidden_fields_excluded(self, introspection_result):
        spec = _build(introspection_result, hidden_fields=["_id", "_full_text"])
        props = (
            spec["components"]["schemas"]["SearchResponse"]
            ["properties"]["result"]["properties"]["records"]
            ["items"]["properties"]
        )
        assert "_id" not in props
        assert "bidding_zone" in props

    def test_underscore_prefix_fields_hidden(self, introspection_result):
        spec = _build(introspection_result)
        props = (
            spec["components"]["schemas"]["SearchResponse"]
            ["properties"]["result"]["properties"]["records"]
            ["items"]["properties"]
        )
        assert "_id" not in props

    def test_data_dictionary_in_description(self, introspection_result):
        spec = _build(introspection_result)
        desc = spec["info"]["description"]
        assert "Data Dictionary" in desc
        assert "bidding_zone" in desc
        assert "15,432" in desc

    def test_title_preserves_names(self, introspection_result):
        spec = _build(introspection_result,
                       dataset_name="Energy Prices",
                       resource_name="Hourly Data")
        title = spec["info"]["title"]
        assert "Energy Prices" in title
        assert "Hourly Data" in title

    def test_empty_introspection(self):
        spec = _build(None)
        assert spec["openapi"] == "3.1.0"
        assert spec["paths"]

    def test_integer_enum_values(self):
        introspection = {
            "fields": [{
                "id": "status_code", "type": "int4", "sample": 200,
                "samples": [200, 404, 500],
                "isEnum": True, "enumValues": [200, 404, 500], "distinctCount": 3,
            }],
            "totalRecords": 100,
            "sampleRecords": [],
        }
        spec = _build(introspection)
        props = (
            spec["components"]["schemas"]["SearchResponse"]
            ["properties"]["result"]["properties"]["records"]
            ["items"]["properties"]
        )
        assert props["status_code"]["enum"] == ["200", "404", "500"]

    def test_none_in_enum_values(self):
        introspection = {
            "fields": [{
                "id": "category", "type": "text", "sample": "A",
                "samples": ["A", "B"],
                "isEnum": True, "enumValues": ["A", None, "B"], "distinctCount": 3,
            }],
            "totalRecords": 50,
            "sampleRecords": [],
        }
        spec = _build(introspection)
        props = (
            spec["components"]["schemas"]["SearchResponse"]
            ["properties"]["result"]["properties"]["records"]
            ["items"]["properties"]
        )
        assert "" in props["category"]["enum"]

    def test_all_fields_hidden(self):
        introspection = {
            "fields": [
                {"id": "_id", "type": "int4", "sample": 1, "samples": [1]},
                {"id": "_full_text", "type": "tsvector", "sample": None, "samples": []},
            ],
            "totalRecords": 10,
            "sampleRecords": [],
        }
        spec = _build(introspection, hidden_fields=["_id", "_full_text"])
        records = (
            spec["components"]["schemas"]["SearchResponse"]
            ["properties"]["result"]["properties"]["records"]
        )
        assert records["items"] == {"type": "object"}


class TestTruncate:
    def test_none_returns_empty(self):
        assert _truncate(None) == ""

    def test_integer_converted(self):
        assert _truncate(42) == "42"

    def test_long_string_truncated(self):
        result = _truncate("x" * 300)
        assert len(result) == 201
        assert result.endswith("\u2026")

    def test_short_string_unchanged(self):
        assert _truncate("hello") == "hello"


class TestSanitiseForTable:
    def test_replaces_pipe(self):
        result = _sanitise_for_table("a|b")
        assert "|" not in result
        assert "a/b" == result

    def test_none_returns_empty(self):
        assert _sanitise_for_table(None) == ""

    def test_newlines_replaced(self):
        result = _sanitise_for_table("line1\nline2")
        assert "\n" not in result

    def test_passthrough(self):
        result = _sanitise_for_table("<script>alert(1)</script>")
        assert result == "<script>alert(1)</script>"


class TestBuildDatasetSpec:
    def _make_resource_spec(self, search_url, introspection):
        return build_resource_spec(
            site_url="https://data.example.com",
            dataset_name="Test",
            resource_name="Resource",
            introspection=introspection,
            search_url=search_url,
        )

    def test_combines_resource_specs(self, introspection_result):
        url1 = "/dataset/ds-001/resource/res-1/search"
        url2 = "/dataset/ds-001/resource/res-2/search"
        spec1 = self._make_resource_spec(url1, introspection_result)
        spec2 = self._make_resource_spec(url2, introspection_result)

        combined = build_dataset_spec(
            site_url="https://data.example.com",
            dataset_name="Test Dataset",
            resource_specs=[("Resource 1", spec1), ("Resource 2", spec2)],
        )

        assert combined["openapi"] == "3.1.0"
        assert "Test Dataset" in combined["info"]["title"]
        assert url1 in combined["paths"]
        assert url2 in combined["paths"]

    def test_schema_names_namespaced(self, introspection_result):
        url1 = "/dataset/ds-001/resource/aaaaaaaa-1111/search"
        url2 = "/dataset/ds-001/resource/bbbbbbbb-2222/search"
        spec1 = self._make_resource_spec(url1, introspection_result)
        spec2 = self._make_resource_spec(url2, introspection_result)

        combined = build_dataset_spec(
            site_url="https://data.example.com",
            dataset_name="Test",
            resource_specs=[("R1", spec1), ("R2", spec2)],
        )

        schemas = combined["components"]["schemas"]
        schema_names = list(schemas.keys())
        assert len(schema_names) == 2
        assert schema_names[0] != schema_names[1]

    def test_operation_ids_unique(self, introspection_result):
        url1 = "/dataset/ds-001/resource/aaaaaaaa-1111/search"
        url2 = "/dataset/ds-001/resource/bbbbbbbb-2222/search"
        spec1 = self._make_resource_spec(url1, introspection_result)
        spec2 = self._make_resource_spec(url2, introspection_result)

        combined = build_dataset_spec(
            site_url="https://data.example.com",
            dataset_name="Test",
            resource_specs=[("R1", spec1), ("R2", spec2)],
        )

        op_ids = []
        for path_item in combined["paths"].values():
            for method_obj in path_item.values():
                if isinstance(method_obj, dict) and "operationId" in method_obj:
                    op_ids.append(method_obj["operationId"])
        assert len(op_ids) == len(set(op_ids))

    def test_input_specs_not_mutated(self, introspection_result):
        url = "/dataset/ds-001/resource/aaaaaaaa-1111/search"
        spec1 = self._make_resource_spec(url, introspection_result)
        original_ref = copy.deepcopy(
            spec1["paths"][url]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]["$ref"]
        )

        build_dataset_spec(
            site_url="https://data.example.com",
            dataset_name="Test",
            resource_specs=[("R1", spec1)],
        )

        current_ref = (
            spec1["paths"][url]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]["$ref"]
        )
        assert current_ref == original_ref
