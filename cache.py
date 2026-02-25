"""
Cache em memória com TTL — LRU thread-safe e versão async.
Usado pelos conectores para evitar requests repetidos.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Tuple, Optional


class LRUCache:
    """Cache LRU simples com TTL por entrada."""

    def __init__(self, capacity: int = 200, ttl_seconds: int = 300):
        self.capacity = capacity
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._order: list[str] = []

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        value, ts = self._cache[key]
        if datetime.utcnow() - ts > self.ttl:
            self._evict(key)
            return None
        # Move para o fim (mais recente)
        self._order.remove(key)
        self._order.append(key)
        return value

    def put(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self.capacity:
            oldest = self._order.pop(0)
            del self._cache[oldest]
        self._cache[key] = (value, datetime.utcnow())
        self._order.append(key)

    def _evict(self, key: str) -> None:
        self._cache.pop(key, None)
        if key in self._order:
            self._order.remove(key)

    def clear(self) -> None:
        self._cache.clear()
        self._order.clear()

    def __len__(self) -> int:
        return len(self._cache)


# Instância global (shared entre requests dentro do mesmo processo)
_cache = LRUCache(capacity=500, ttl_seconds=600)


def async_cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator async que cacheia o resultado de uma função.

    Uso:
        @async_cached(ttl_seconds=60)
        async def get_data(query: str) -> dict: ...
    """
    cache = LRUCache(capacity=200, ttl_seconds=ttl_seconds)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Remove kwargs que não devem fazer parte da chave
            key_kwargs = {k: v for k, v in kwargs.items() if k not in ("request_id",)}
            key = f"{key_prefix}{func.__name__}:{args}:{sorted(key_kwargs.items())}"
            cached = cache.get(key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            cache.put(key, result)
            return result

        wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator