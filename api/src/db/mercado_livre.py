from typing import Dict, Any, List
from .base import MarketplaceRules

class MercadoLivreRules(MarketplaceRules):
    """Validation rules for Mercado Livre."""

    def validate_title(self, title: str) -> Dict[str, Any]:
        max_length = 60
        issues = []
        
        if not title:
            return {"valid": False, "issues": ["Title is empty"], "score": 0}

        if len(title) > max_length:
            issues.append(f"Title exceeds {max_length} characters (current: {len(title)})")
        
        # Termos promocionais proibidos no título pelo ML
        prohibited_terms = ["promoção", "oferta", "envio grátis", "frete grátis", "compra garantida", "brinde"]
        for term in prohibited_terms:
            if term.lower() in title.lower():
                issues.append(f"Title contains prohibited promotional term: '{term}'")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "length": len(title),
            "max_length": max_length
        }

    def get_mandatory_attributes(self, category_id: str) -> List[str]:
        # Em produção, isso consultaria a API do ML: /categories/{id}/attributes
        # Para o MVP, retornamos atributos comuns obrigatórios na maioria das categorias
        return ["BRAND", "MODEL", "ITEM_CONDITION"]

    def validate_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        
        # 1. Validação de Título
        title = listing_data.get("title", "")
        title_res = self.validate_title(title)
        if not title_res["valid"]:
            issues.extend(title_res["issues"])

        # 2. Validação de Atributos
        attributes = listing_data.get("attributes", [])
        existing_attr_ids = set()
        
        # Normaliza lista de atributos para set de IDs
        if isinstance(attributes, list):
            for attr in attributes:
                if isinstance(attr, dict) and "id" in attr:
                    existing_attr_ids.add(attr["id"])
        elif isinstance(attributes, dict):
            existing_attr_ids = set(attributes.keys())

        category_id = listing_data.get("category_id", "")
        mandatory_attrs = self.get_mandatory_attributes(category_id)
        
        for req_id in mandatory_attrs:
            if req_id not in existing_attr_ids:
                issues.append(f"Missing mandatory attribute: {req_id}")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }