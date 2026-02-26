"""Database package public surface.

This package keeps:
- `repository` for Supabase V5 persistence
- marketplace rules helpers for legacy validations
"""

from api.src.db import repository

try:
    from api.src.db.base import MarketplaceRules
    from api.src.db.mercado_livre import MercadoLivreRules
except Exception:
    MarketplaceRules = None  # type: ignore
    MercadoLivreRules = None  # type: ignore


def get_rules(marketplace: str):
    """Factory for legacy rules usage."""
    if marketplace == "mercado_livre" and MercadoLivreRules:
        return MercadoLivreRules()
    raise ValueError(f"No rules defined for marketplace: {marketplace}")


__all__ = ["repository", "get_rules", "MarketplaceRules"]
