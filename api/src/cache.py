"""Compat cache exports for legacy imports."""

from cache import async_cached


def async_lru_cache(ttl_seconds: int = 300, key_prefix: str = ""):
    return async_cached(ttl_seconds=ttl_seconds, key_prefix=key_prefix)
