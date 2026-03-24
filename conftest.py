import sys
import types
from unittest.mock import MagicMock


def _make_module(name, attrs=None):
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    return mod


def _install_mock_modules():
    if "ckan" in sys.modules:
        return

    # dogpile.cache — minimal in-memory implementation
    class _NO_VALUE_TYPE:
        def __repr__(self):
            return "<NO_VALUE>"

    NO_VALUE = _NO_VALUE_TYPE()

    class _MemoryRegion:
        def __init__(self):
            self._store = {}
            self.serializer = None
            self.deserializer = None

        def configure(self, backend, **kw):
            return self

        def get(self, key):
            return self._store.get(key, NO_VALUE)

        def set(self, key, value):
            self._store[key] = value

        def delete(self, key):
            self._store.pop(key, None)

    def _make_region():
        return _MemoryRegion()

    dogpile = _make_module("dogpile")
    dogpile_cache = _make_module("dogpile.cache")
    dogpile_cache.make_region = _make_region
    dogpile_cache_api = _make_module("dogpile.cache.api", {"NO_VALUE": NO_VALUE})
    dogpile.cache = dogpile_cache
    sys.modules["dogpile"] = dogpile
    sys.modules["dogpile.cache"] = dogpile_cache
    sys.modules["dogpile.cache.api"] = dogpile_cache_api

    # sqlalchemy
    if "sqlalchemy" not in sys.modules:
        sa = _make_module("sqlalchemy")
        sa.text = MagicMock(side_effect=lambda s: s)
        sa.create_engine = MagicMock()
        sys.modules["sqlalchemy"] = sa

    # ckan module hierarchy
    ckan = _make_module("ckan")
    ckan_plugins = _make_module("ckan.plugins")
    ckan_plugins_toolkit = _make_module("ckan.plugins.toolkit")
    ckan_logic = _make_module("ckan.logic")
    ckan_common = _make_module("ckan.common")

    # toolkit attributes
    toolkit = ckan_plugins_toolkit
    toolkit.get_action = MagicMock()
    toolkit.check_access = MagicMock()
    toolkit.get_or_bust = MagicMock(side_effect=lambda d, k: d[k])
    toolkit.url_for = MagicMock(return_value="/mocked-url")
    toolkit.render = MagicMock(return_value="<html></html>")
    toolkit.abort = MagicMock()
    toolkit.config = MagicMock()
    toolkit.config.get = MagicMock(return_value="")
    toolkit.asbool = MagicMock(return_value=True)
    toolkit.g = MagicMock()
    toolkit.add_template_directory = MagicMock()
    toolkit.add_public_directory = MagicMock()
    toolkit.ObjectNotFound = type("ObjectNotFound", (Exception,), {})
    toolkit.NotAuthorized = type("NotAuthorized", (Exception,), {})
    toolkit.ValidationError = type("ValidationError", (Exception,), {"error_dict": {}})

    # auth decorators
    toolkit.auth_allow_anonymous_access = lambda fn: fn

    # plugins
    ckan_plugins.SingletonPlugin = type("SingletonPlugin", (), {})
    ckan_plugins.implements = MagicMock()
    ckan_plugins.toolkit = toolkit
    ckan_plugins.IConfigurer = MagicMock()
    ckan_plugins.IActions = MagicMock()
    ckan_plugins.IAuthFunctions = MagicMock()
    ckan_plugins.IBlueprint = MagicMock()
    ckan_plugins.IPackageController = MagicMock()
    ckan_plugins.IResourceController = MagicMock()
    ckan_plugins.ITemplateHelpers = MagicMock()

    # logic
    ckan_logic.side_effect_free = lambda fn: fn

    # common
    ckan_common.config = MagicMock()

    # Wire up
    ckan.plugins = ckan_plugins
    ckan.logic = ckan_logic
    ckan.common = ckan_common

    sys.modules["ckan"] = ckan
    sys.modules["ckan.plugins"] = ckan_plugins
    sys.modules["ckan.plugins.toolkit"] = ckan_plugins_toolkit
    sys.modules["ckan.logic"] = ckan_logic
    sys.modules["ckan.common"] = ckan_common


_install_mock_modules()
