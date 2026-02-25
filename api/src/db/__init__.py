from .base import MarketplaceRules
from .mercado_livre import MercadoLivreRules

def get_rules(marketplace: str) -> MarketplaceRules:
    """Factory to get rules instance by marketplace name."""
    if marketplace == "mercado_livre":
        return MercadoLivreRules()
    # Futuro: Adicionar Magalu, Amazon, etc.
    raise ValueError(f"No rules defined for marketplace: {marketplace}")