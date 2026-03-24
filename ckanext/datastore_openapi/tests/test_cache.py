import json
from unittest.mock import patch

from dogpile.cache.api import NO_VALUE

from ckanext.datastore_openapi.cache import (
    _json_serializer,
    _json_deserializer,
    resource_cache_key,
    get_cached,
    set_cached,
    invalidate,
    invalidate_resource,
)


class TestJsonSerializer:
    def test_returns_bytes(self):
        result = _json_serializer({"key": "value"})
        assert isinstance(result, bytes)
        assert json.loads(result) == {"key": "value"}

    def test_nested_structure(self):
        data = {"openapi": "3.1.0", "paths": {"/api": {"get": {}}}}
        assert json.loads(_json_serializer(data)) == data


class TestJsonDeserializer:
    def test_valid_json(self):
        assert _json_deserializer(b'{"key": "value"}') == {"key": "value"}

    def test_invalid_json_returns_no_value(self):
        assert _json_deserializer(b"not json{{{") is NO_VALUE

    def test_none_returns_no_value(self):
        assert _json_deserializer(None) is NO_VALUE

    def test_bad_encoding_returns_no_value(self):
        assert _json_deserializer(b"\x80\x81\x82") is NO_VALUE


class TestCacheKeys:
    def test_resource_key_format(self):
        assert resource_cache_key("abc-123") == "datastore_openapi:resource:abc-123"


def _config_side_effect(key, default=None):
    return default


class TestCacheRoundTrip:
    @patch("ckanext.datastore_openapi.cache.toolkit")
    def test_set_then_get(self, mock_toolkit):
        mock_toolkit.config.get.side_effect = _config_side_effect
        import ckanext.datastore_openapi.cache as cache_mod
        cache_mod._region = None

        key = "test:roundtrip:1"
        data = {"openapi": "3.1.0", "paths": {}}
        set_cached(key, data)
        result = get_cached(key)
        assert result == data

    @patch("ckanext.datastore_openapi.cache.toolkit")
    def test_invalidate_removes_entry(self, mock_toolkit):
        mock_toolkit.config.get.side_effect = _config_side_effect
        import ckanext.datastore_openapi.cache as cache_mod
        cache_mod._region = None

        key = "test:roundtrip:2"
        set_cached(key, {"data": True})
        invalidate(key)
        assert get_cached(key) is NO_VALUE

    @patch("ckanext.datastore_openapi.cache.toolkit")
    def test_miss_returns_no_value(self, mock_toolkit):
        mock_toolkit.config.get.side_effect = _config_side_effect
        import ckanext.datastore_openapi.cache as cache_mod
        cache_mod._region = None

        assert get_cached("test:nonexistent") is NO_VALUE

    @patch("ckanext.datastore_openapi.cache.toolkit")
    def test_invalidate_resource_convenience(self, mock_toolkit):
        mock_toolkit.config.get.side_effect = _config_side_effect
        import ckanext.datastore_openapi.cache as cache_mod
        cache_mod._region = None

        key = resource_cache_key("res-999")
        set_cached(key, {"cached": True})
        invalidate_resource("res-999")
        assert get_cached(key) is NO_VALUE
