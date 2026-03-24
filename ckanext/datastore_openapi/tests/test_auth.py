from ckanext.datastore_openapi.auth import (
    datastore_openapi_resource_show,
    datastore_openapi_dataset_show,
    datastore_openapi_cache_invalidate,
)


def test_resource_show_allows_anonymous():
    result = datastore_openapi_resource_show({}, {})
    assert result == {"success": True}


def test_dataset_show_allows_anonymous():
    result = datastore_openapi_dataset_show({}, {})
    assert result == {"success": True}


def test_cache_invalidate_denies_by_default():
    result = datastore_openapi_cache_invalidate({}, {})
    assert result == {"success": False}


def test_auth_functions_do_not_call_check_access():
    # Auth functions define the policy — they must not call check_access themselves.
    # Verify by inspecting the source: no toolkit imports needed, functions are pure.
    import inspect
    for fn in (datastore_openapi_resource_show, datastore_openapi_dataset_show,
               datastore_openapi_cache_invalidate):
        src = inspect.getsource(fn)
        assert "check_access" not in src
