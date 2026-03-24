import json
import logging

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE

import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

_region = None


def _json_serializer(value):
    return json.dumps(value).encode("utf-8")


def _json_deserializer(raw):
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        log.warning("Cache deserializer failed, treating as miss")
        return NO_VALUE


def _cfg(key, default=None):
    return toolkit.config.get(f"ckanext.datastore_openapi.{key}", default)


def get_region():
    global _region
    if _region is not None:
        return _region

    backend = _cfg("cache.backend", "dogpile.cache.memory")
    expiry = int(_cfg("cache.expiry", 3600))

    arguments = {}
    if backend == "dogpile.cache.redis":
        redis_url = _cfg(
            "cache.redis_url",
            toolkit.config.get("ckan.redis.url", "redis://localhost:6379/1"),
        )
        arguments = {
            "url": redis_url,
            "redis_expiration_time": expiry + 60,
            "distributed_lock": True,
        }

    _region = make_region().configure(
        backend,
        expiration_time=expiry,
        arguments=arguments,
    )
    _region.serializer = _json_serializer
    _region.deserializer = _json_deserializer

    log.info("Cache configured: backend=%s, expiry=%ds", backend, expiry)
    return _region


def resource_cache_key(resource_id):
    return f"datastore_openapi:resource:{resource_id}"


def get_cached(key):
    region = get_region()
    value = region.get(key)
    log.debug("Cache %s: %s", "hit" if value is not NO_VALUE else "miss", key)
    return value


def set_cached(key, value):
    get_region().set(key, value)


def invalidate(key):
    get_region().delete(key)


def invalidate_resource(resource_id):
    invalidate(resource_cache_key(resource_id))
