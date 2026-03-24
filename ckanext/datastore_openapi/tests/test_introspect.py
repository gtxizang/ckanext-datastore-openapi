from unittest.mock import patch, MagicMock

from ckanext.datastore_openapi.introspect import _parse_pg_array, _query_pg_stats, introspect


class TestParsePgArray:
    def test_simple_array(self):
        assert _parse_pg_array("{a,b,c}") == ["a", "b", "c"]

    def test_numeric_array(self):
        assert _parse_pg_array("{1,2,3}") == ["1", "2", "3"]

    def test_empty_array(self):
        assert _parse_pg_array("{}") == []

    def test_none_returns_empty(self):
        assert _parse_pg_array(None) == []

    def test_already_list(self):
        assert _parse_pg_array(["a", "b"]) == ["a", "b"]

    def test_already_tuple(self):
        assert _parse_pg_array(("x", "y")) == ["x", "y"]

    def test_quoted_values(self):
        assert _parse_pg_array('{"foo bar",baz}') == ["foo bar", "baz"]

    def test_quoted_with_comma(self):
        assert _parse_pg_array('{"a,b","c"}') == ["a,b", "c"]

    def test_escaped_quotes(self):
        assert _parse_pg_array('{"say \\"hello\\"",other}') == ['say "hello"', "other"]

    def test_null_handling(self):
        result = _parse_pg_array("{a,NULL,b}")
        assert result == ["a", "b"]

    def test_single_element(self):
        assert _parse_pg_array("{single}") == ["single"]

    def test_non_array_string(self):
        assert _parse_pg_array("not an array") == []


class TestQueryPgStats:
    def test_parses_rows_correctly(self):
        mock_row = (
            "bidding_zone",
            4.0,
            "{SE1,SE2,SE3,SE4}",
            None,
        )
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [mock_row]
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        stats = _query_pg_stats(mock_engine, "test-resource")

        assert "bidding_zone" in stats
        assert stats["bidding_zone"]["n_distinct"] == 4.0
        assert stats["bidding_zone"]["most_common_vals"] == ["SE1", "SE2", "SE3", "SE4"]
        assert stats["bidding_zone"]["histogram_bounds"] == []

    def test_uses_bind_params(self):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        _query_pg_stats(mock_engine, "my-resource-id")

        call_args = mock_conn.execute.call_args
        assert call_args[0][1] == {"table_name": "my-resource-id"}


class TestIntrospect:
    @patch("ckanext.datastore_openapi.introspect._get_datastore_engine")
    @patch("ckanext.datastore_openapi.introspect.toolkit")
    def test_returns_none_on_meta_failure(self, mock_toolkit, mock_engine):
        mock_toolkit.get_action.return_value = MagicMock(
            side_effect=Exception("DataStore not found")
        )
        result = introspect("test-resource-id")
        assert result is None

    @patch("ckanext.datastore_openapi.introspect._get_datastore_engine")
    @patch("ckanext.datastore_openapi.introspect._query_pg_stats")
    @patch("ckanext.datastore_openapi.introspect.toolkit")
    def test_enum_detection_from_pg_stats(self, mock_toolkit, mock_pg_stats, mock_engine):
        meta_result = {
            "fields": [
                {"id": "status", "type": "text"},
            ],
            "total": 100,
        }
        sample_result = {"records": [{"status": "active"}]}

        def mock_action(action_name):
            def fn(ctx, data):
                if action_name == "datastore_search":
                    return meta_result if data.get("limit") == 0 else sample_result
                if action_name == "datastore_info":
                    raise Exception("not available")
                return {}
            return fn

        mock_toolkit.get_action.side_effect = mock_action
        mock_engine.return_value = MagicMock()
        mock_pg_stats.return_value = {
            "status": {
                "n_distinct": 3,
                "most_common_vals": ["active", "pending", "closed"],
                "histogram_bounds": [],
            },
        }

        result = introspect("res-1", config={"hidden_fields": set(), "enum_threshold": 25, "max_fields": 50})

        status = next(f for f in result["fields"] if f["id"] == "status")
        assert status["isEnum"] is True
        assert status["enumValues"] == ["active", "pending", "closed"]
        assert status["distinctCount"] == 3

    @patch("ckanext.datastore_openapi.introspect._get_datastore_engine")
    @patch("ckanext.datastore_openapi.introspect._query_pg_stats")
    @patch("ckanext.datastore_openapi.introspect.toolkit")
    def test_range_detection_from_histogram_bounds(self, mock_toolkit, mock_pg_stats, mock_engine):
        meta_result = {
            "fields": [{"id": "price", "type": "float8"}],
            "total": 500,
        }
        sample_result = {"records": [{"price": 42.5}]}

        def mock_action(action_name):
            def fn(ctx, data):
                if action_name == "datastore_search":
                    return meta_result if data.get("limit") == 0 else sample_result
                if action_name == "datastore_info":
                    raise Exception("not available")
                return {}
            return fn

        mock_toolkit.get_action.side_effect = mock_action
        mock_engine.return_value = MagicMock()
        mock_pg_stats.return_value = {
            "price": {
                "n_distinct": -0.95,
                "most_common_vals": [],
                "histogram_bounds": ["0.0", "50.0", "100.0"],
            },
        }

        result = introspect("res-1", config={"hidden_fields": set(), "enum_threshold": 25, "max_fields": 50})

        price = next(f for f in result["fields"] if f["id"] == "price")
        assert price["min"] == "0.0"
        assert price["max"] == "100.0"

    @patch("ckanext.datastore_openapi.introspect._get_datastore_engine")
    @patch("ckanext.datastore_openapi.introspect.toolkit")
    def test_hidden_fields_skipped_for_enrichment(self, mock_toolkit, mock_engine):
        meta_result = {
            "fields": [
                {"id": "_id", "type": "int4"},
                {"id": "_full_text", "type": "tsvector"},
                {"id": "name", "type": "text"},
            ],
            "total": 10,
        }

        def mock_action(action_name):
            def fn(ctx, data):
                if action_name == "datastore_search":
                    return meta_result if data.get("limit") == 0 else {"records": []}
                if action_name == "datastore_info":
                    raise Exception("not available")
                return {}
            return fn

        mock_toolkit.get_action.side_effect = mock_action
        mock_engine.return_value = None

        result = introspect("res-1")

        hidden = next(f for f in result["fields"] if f["id"] == "_id")
        assert "isEnum" not in hidden
        assert "min" not in hidden

    @patch("ckanext.datastore_openapi.introspect._get_datastore_engine")
    @patch("ckanext.datastore_openapi.introspect.toolkit")
    def test_datastore_info_used_as_primary_source(self, mock_toolkit, mock_engine):
        meta_result = {
            "fields": [{"id": "price", "type": "float8"}],
            "total": 100,
        }
        ds_info_result = {
            "fields": [{"id": "price", "min": 10.0, "max": 200.0}],
        }

        def mock_action(action_name):
            def fn(ctx, data):
                if action_name == "datastore_search":
                    return meta_result if data.get("limit") == 0 else {"records": []}
                if action_name == "datastore_info":
                    return ds_info_result
                return {}
            return fn

        mock_toolkit.get_action.side_effect = mock_action

        result = introspect("res-1", config={"hidden_fields": set(), "enum_threshold": 25, "max_fields": 50})

        price = next(f for f in result["fields"] if f["id"] == "price")
        assert price["min"] == 10.0
        assert price["max"] == 200.0
        mock_engine.assert_not_called()

    @patch("ckanext.datastore_openapi.introspect._get_datastore_engine")
    @patch("ckanext.datastore_openapi.introspect.toolkit")
    def test_max_fields_respected(self, mock_toolkit, mock_engine):
        fields = [{"id": f"col_{i}", "type": "text"} for i in range(100)]
        meta_result = {"fields": fields, "total": 100}

        def mock_action(action_name):
            def fn(ctx, data):
                if action_name == "datastore_search":
                    return meta_result if data.get("limit") == 0 else {"records": []}
                if action_name == "datastore_info":
                    raise Exception("not available")
                return {}
            return fn

        mock_toolkit.get_action.side_effect = mock_action
        mock_engine.return_value = None

        result = introspect("res-1", config={"hidden_fields": set(), "enum_threshold": 25, "max_fields": 10})

        assert len(result["fields"]) == 10

    @patch("ckanext.datastore_openapi.introspect._get_datastore_engine")
    @patch("ckanext.datastore_openapi.introspect.toolkit")
    def test_total_records_and_samples_included(self, mock_toolkit, mock_engine):
        meta_result = {"fields": [{"id": "x", "type": "text"}], "total": 42}
        sample_result = {"records": [{"x": "hello"}, {"x": "world"}]}

        def mock_action(action_name):
            def fn(ctx, data):
                if action_name == "datastore_search":
                    return meta_result if data.get("limit") == 0 else sample_result
                if action_name == "datastore_info":
                    raise Exception("not available")
                return {}
            return fn

        mock_toolkit.get_action.side_effect = mock_action
        mock_engine.return_value = None

        result = introspect("res-1", config={"hidden_fields": set(), "enum_threshold": 25, "max_fields": 50})

        assert result["totalRecords"] == 42
        assert len(result["sampleRecords"]) == 2
