from ckanext.datastore_openapi.type_map import (
    pg_to_jsonschema,
    TEXT_TYPES,
    NUMERIC_TYPES,
    TIMESTAMP_TYPES,
    RANGE_TYPES,
)


class TestPgToJsonschema:
    def test_text(self):
        assert pg_to_jsonschema("text") == {"type": "string"}

    def test_varchar(self):
        assert pg_to_jsonschema("varchar") == {"type": "string"}

    def test_int4(self):
        assert pg_to_jsonschema("int4") == {"type": "integer"}

    def test_int8_has_format(self):
        result = pg_to_jsonschema("int8")
        assert result["type"] == "integer"
        assert result["format"] == "int64"

    def test_float8(self):
        result = pg_to_jsonschema("float8")
        assert result["type"] == "number"
        assert result["format"] == "double"

    def test_bool(self):
        assert pg_to_jsonschema("bool") == {"type": "boolean"}

    def test_boolean(self):
        assert pg_to_jsonschema("boolean") == {"type": "boolean"}

    def test_timestamp(self):
        result = pg_to_jsonschema("timestamp")
        assert result["type"] == "string"
        assert result["format"] == "date-time"

    def test_timestamptz(self):
        result = pg_to_jsonschema("timestamptz")
        assert result["type"] == "string"
        assert result["format"] == "date-time"

    def test_date(self):
        result = pg_to_jsonschema("date")
        assert result["type"] == "string"
        assert result["format"] == "date"

    def test_uuid(self):
        result = pg_to_jsonschema("uuid")
        assert result["type"] == "string"
        assert result["format"] == "uuid"

    def test_json(self):
        assert pg_to_jsonschema("json") == {"type": "object"}

    def test_jsonb(self):
        assert pg_to_jsonschema("jsonb") == {"type": "object"}

    def test_array_text(self):
        result = pg_to_jsonschema("_text")
        assert result["type"] == "array"
        assert result["items"] == {"type": "string"}

    def test_array_int4(self):
        result = pg_to_jsonschema("_int4")
        assert result["type"] == "array"
        assert result["items"] == {"type": "integer"}

    def test_unknown_type_falls_back_to_string(self):
        assert pg_to_jsonschema("geometry") == {"type": "string"}

    def test_case_insensitive(self):
        assert pg_to_jsonschema("TEXT") == {"type": "string"}
        assert pg_to_jsonschema("Int4") == {"type": "integer"}

    def test_strips_whitespace(self):
        assert pg_to_jsonschema("  text  ") == {"type": "string"}


class TestTypeConstants:
    def test_text_types(self):
        assert "text" in TEXT_TYPES
        assert "varchar" in TEXT_TYPES
        assert "citext" in TEXT_TYPES
        assert "int4" not in TEXT_TYPES

    def test_numeric_types(self):
        assert "int4" in NUMERIC_TYPES
        assert "float8" in NUMERIC_TYPES
        assert "numeric" in NUMERIC_TYPES
        assert "text" not in NUMERIC_TYPES

    def test_timestamp_types(self):
        assert "timestamp" in TIMESTAMP_TYPES
        assert "timestamptz" in TIMESTAMP_TYPES
        assert "date" in TIMESTAMP_TYPES

    def test_range_types_is_union(self):
        assert RANGE_TYPES == NUMERIC_TYPES | TIMESTAMP_TYPES
