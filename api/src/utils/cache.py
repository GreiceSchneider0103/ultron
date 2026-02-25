"""
Shim to keep backward compatible import:
from api.src.utils.cache import async_lru_cache
"""
try:
    # If you already have a real cache implementation inside api/src, import it here.
    from api.src.cache import async_lru_cache  # type: ignore
except Exception:
    # Fallback: import the repo-root cache.py (C:\Users\Usuario\ultron\cache.py)
    from cache import async_lru_cache  # type: ignore
