import asyncio
from functools import wraps
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

class LRUCache:
    def __init__(self, capacity: int = 100, ttl_seconds: int = 300):
        self.capacity = capacity
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.access_order = []

    def get(self, key: str) -> Any:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                self.access_order.remove(key)
                self.access_order.append(key)
                return value
            else:
                self.remove(key)
        return None

    def put(self, key: str, value: Any):
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        
        self.cache[key] = (value, datetime.now())
        self.access_order.append(key)

    def remove(self, key: str):
        if key in self.cache:
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)

_global_cache = LRUCache()

def async_lru_cache(ttl_seconds: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Exclude request_id from cache key to allow hits across requests
            key_kwargs = {k: v for k, v in kwargs.items() if k != "request_id"}
            key = f"{func.__name__}:{args}:{key_kwargs}"
            cached_val = _global_cache.get(key)
            if cached_val is not None:
                return cached_val
            
            result = await func(*args, **kwargs)
            _global_cache.put(key, result)
            return result
        return wrapper
    return decorator