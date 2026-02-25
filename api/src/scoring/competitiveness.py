"""
Motor de Scoring - Competitividade
"""

from typing import List, Dict, Any
from api.src.types.listing import ListingNormalized


class CompetitivenessScorer:
    """
    Calcula score de competitividade vs concorrentes.
    
    Critérios:
    - Posição de preço
    - Diferenciais (frete, badges)
    - Qualidade geral vs preço
    """
    
    def score(
        self,
        listing: ListingNormalized,
        competitors: List[ListingNormalized]
    ) -> Dict[str, Any]:
        
        if not competitors:
            return {
                "score": 50.0,
                "factors": {},
                "suggestions": ["Sem concorrentes para comparar"],
                "grade": "C"
            }
        
        # Calcular estatísticas dos concorrentes
        prices = [c.price for c in competitors]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        factors = {}
        
        # 1. Score de preço
        price_score = self._score_price(listing.price, avg_price, min_price, max_price)
        factors["price"] = price_score
        
        # 2. Score de valor
        value_score = self._score_value(listing, competitors)
        factors["value"] = value_score
        
        # 3. Score de posição
        position_score = self._score_position(listing.price, min_price, max_price)
        factors["position"] = position_score
        
        # Score final
        final_score = (price_score["score"] * 0.4 + 
                      value_score["score"] * 0.35 + 
                      position_score["score"] * 0.25)
        
        suggestions = self._generate_suggestions(factors, listing, avg_price)
        
        return {
            "score": round(final_score, 1),
            "factors": factors,
            "suggestions": suggestions,
            "grade": self._get_grade(final_score),
            "market_stats": {
                "avg_price": avg_price,
                "min_price": min_price,
                "max_price": max_price,
                "my_price": listing.price,
                "vs_avg": round((listing.price - avg_price) / avg_price * 100, 1)
            }
        }
    
    def _score_price(
        self,
        my_price: float,
        avg_price: float,
        min_price: float,
        max_price: float
    ) -> Dict[str, Any]:
        """Avaliar preço vs média"""
        
        diff_pct = (my_price - avg_price) / avg_price * 100
        
        score = 0
        feedback = []
        
        if diff_pct <= -20:  # Muito mais barato
            score = 100
            feedback = "Preço muito competitivo"
        elif diff_pct <= -10:  # Mais barato
            score = 85
        elif diff_pct <= 0:  # Na média ou sedikit cheaper
            score = 70
        elif diff_pct <= 10:  # Levemente mais caro
            score = 50
            feedback = "Preço acima da média"
        elif diff_pct <= 20:  # Mais caro
            score = 30
            feedback = "Preço significativamente acima"
        else:  # Muito mais caro
            score = 10
            feedback = "Preço muito acima - justifique os motivos"
        
        return {
            "score": score,
            "my_price": my_price,
            "avg_price": avg_price,
            "diff_pct": round(diff_pct, 1),
            "feedback": feedback
        }
    
    def _score_value(
        self,
        listing: ListingNormalized,
        competitors: List[ListingNormalized]
    ) -> Dict[str, Any]:
        """Avaliar valor (preço vs benefícios)"""
        
        # Contar diferenciais
        my_benefits = 0
        
        if listing.badges.frete_gratis:
            my_benefits += 2
        if listing.badges.full:
            my_benefits += 2
        if listing.badges.oficial:
            my_benefits += 2
        if listing.badges.premium:
            my_benefits += 1
        if listing.social_proof.avaliacoes >= 10:
            my_benefits += 1
        if listing.social_proof.nota_media >= 4.5:
            my_benefits += 1
        if len(listing.media) >= 5:
            my_benefits += 1
        
        # Média de benefícios dos concorrentes
        comp_benefits = []
        for c in competitors:
            b = 0
            if c.badges.frete_gratis:
                b += 2
            if c.badges.full:
                b += 2
            if c.badges.oficial:
                b += 2
            if c.badges.premium:
                b += 1
            if c.social_proof.avaliacoes >= 10:
                b += 1
            if c.social_proof.nota_media >= 4.5:
                b += 1
            if len(c.media) >= 5:
                b += 1
            comp_benefits.append(b)
        
        avg_benefits = sum(comp_benefits) / len(comp_benefits) if comp_benefits else 0
        
        score = min(100, (my_benefits / max(avg_benefits, 1)) * 50)
        
        return {
            "score": round(score, 1),
            "my_benefits": my_benefits,
            "avg_benefits": round(avg_benefits, 1)
        }
    
    def _score_position(
        self,
        my_price: float,
        min_price: float,
        max_price: float
    ) -> Dict[str, Any]:
        """Avaliar posição no mercado"""
        
        if min_price == max_price:
            return {"score": 50, "position": "monopoly"}
        
        position = (my_price - min_price) / (max_price - min_price) * 100
        
        if position <= 10:
            score = 100
            position_desc = "Mais barato"
        elif position <= 30:
            score = 80
            position_desc = "Abaixo da média"
        elif position <= 50:
            score = 60
            position_desc = "Na média"
        elif position <= 70:
            score = 40
            position_desc = "Acima da média"
        elif position <= 90:
            score = 20
            position_desc = "Premium"
        else:
            score = 10
            position_desc = "Mais caro do mercado"
        
        return {
            "score": score,
            "position": round(position, 1),
            "description": position_desc
        }
    
    def _generate_suggestions(
        self,
        factors: Dict,
        listing: ListingNormalized,
        avg_price: float
    ) -> List[str]:
        """Gerar sugestões"""
        
        suggestions = []
        
        # Sugestão de preço
        if factors.get("price", {}).get("diff_pct", 0) > 10:
            my_price = listing.price
            suggested = avg_price * 0.95
            suggestions.append(
                f"Considere reduzir preço para R$ {suggested:.2f} "
                f"({((my_price - suggested) / my_price * 100):.0f}% de redução)"
            )
        
        # Sugestão de benefícios
        if not listing.badges.frete_gratis:
            suggestions.append("Adicionar frete grátis para competir melhor")
        
        if not listing.badges.full:
            suggestions.append("Considere usar fulfillment full")
        
        return suggestions
    
    def _get_grade(self, score: float) -> str:
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
