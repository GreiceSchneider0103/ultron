"""Deprecated wrapper entrypoint.

Use `uvicorn api.src.main:app --reload`.
"""

from api.src.main import app

__all__ = ["app"]
