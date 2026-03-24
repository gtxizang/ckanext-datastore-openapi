import json

from ckanext.datastore_openapi.blueprints import _json_response, _error_response


class TestJsonResponse:
    def test_wraps_in_ckan_envelope(self):
        resp = _json_response({"key": "value"})
        body = json.loads(resp.get_data(as_text=True))
        assert body["success"] is True
        assert body["result"] == {"key": "value"}
        assert resp.status_code == 200
        assert "application/json" in resp.content_type

    def test_custom_status(self):
        resp = _json_response({"data": True}, status=201)
        assert resp.status_code == 201


class TestErrorResponse:
    def test_400_validation_error(self):
        resp = _error_response("Bad input", 400)
        body = json.loads(resp.get_data(as_text=True))
        assert body["success"] is False
        assert body["error"]["message"] == "Bad input"
        assert body["error"]["__type"] == "Validation Error"
        assert resp.status_code == 400

    def test_404_not_found(self):
        resp = _error_response("Missing", 404)
        body = json.loads(resp.get_data(as_text=True))
        assert body["error"]["__type"] == "Not Found"
        assert resp.status_code == 404

    def test_default_status_is_404(self):
        resp = _error_response("Gone")
        assert resp.status_code == 404

    def test_unknown_status_defaults_to_not_found_type(self):
        resp = _error_response("Server error", 500)
        body = json.loads(resp.get_data(as_text=True))
        assert body["error"]["__type"] == "Not Found"
