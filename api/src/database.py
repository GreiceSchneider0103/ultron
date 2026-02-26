"""Deprecated database module kept for compatibility.

Real persistence lives in api.src.db.repository.
"""

from api.src.db import repository


def init_db() -> None:
    """No-op compatibility shim."""
    return None


def save_research_run(summary, listings):
    """Persist minimal research payload to V5 tables through repository."""
    return repository.create_market_research_audit(summary=summary, listings=listings)
