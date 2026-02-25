"""
Shim module to maintain backward compatibility with imports like:
from api.src.db import repository
or
from api.src.db.repository import ...

This file intentionally re-exports the current repository module.
It also provides SAFE fallback stubs for legacy functions that may not
exist yet in api.src.repository (e.g., upsert_listing).

Rule: additive changes only; do not break existing public imports.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Re-export everything that exists in the real repository implementation.
from api.src.repository import *  # noqa


def upsert_listing(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    SAFE fallback stub.

    Some parts of the codebase may import `upsert_listing`, but the current
    `api.src.repository` doesn't implement it yet.

    Behavior:
    - Returns a dict with ok=False so callers can handle gracefully.
    - Does NOT write to DB. (Keeps patch non-invasive.)
    """
    return {
        "ok": False,
        "reason": "upsert_listing_not_implemented",
        "args_len": len(args),
        "kwargs_keys": list(kwargs.keys()),
    }


def get_listing(*args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """
    SAFE fallback stub for read path (if any code expects it).
    """
    return None