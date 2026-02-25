"""
Motor de Scoring - Conversão
"""

from typing import List, Dict, Any
from api.src.types.listing import ListingNormalized


class ConversionScorer:
    """
    Calcula score de conversão para anúncios.
    
    Critérios avaliados:
    - Prova social (reviews, rating)
    - Selos (frete, oficial, full)
    - Texto (bullets, descrição)
    - Vendedor (reputação)
    """
    
    def score(
        self,
        listing: ListingNormalized,
        competitors: List[ListingNormalized]
    ) -> Dict[str, Any]:
        """
        Calcular score de conversão.
        """
        
        factors = {}
        
        # 1. Prova social
        social_score = self._score_social(listing)
        factors["social"] = social_score
        
        # 2. Selos
        badges_score = self._score_badges(listing)
        factors["badges"] = badges_score
        
        # 3. Texto
        text_score = self._score_text(listing)
        factors["text"] = text_score
        
        # 4. Vendedor
        seller_score = self._score_seller(listing)
        factors["seller"] = seller_score
        
        # Score final
        weights = {
            "social": 0.30,
            "badges": 0.30,
            "text": 0.20,
            "seller": 0.20
        }
        
        final_score = sum(
            factors[k]["score"] * weights[k]
            for k in weights
        )
        
        suggestions = self._generate_suggestions(factors)
        
        return {
            "score": round(final_score, 1),
            "factors": factors,
            "suggestions": suggestions,
            "grade": self._get_grade(final_score)
        }
    
    def _score_social(self, listing: ListingNormalized) -> Dict[str, Any]:
        """Avaliar prova social"""
        
        social = listing.social_proof
        score = 0
        feedback = []
        
        # Avaliações
        if social.avaliacoes >= 100:
            score += 40
        elif social.avaliacoes >= 50:
            score += 30
        elif social.avaliacoes >= 10:
            score += 15
        elif social.avaliacoes > 0:
            score += 5
        else:
            feedback.append("Sem avaliações")
        
        # Nota média
        if social.nota_media >= 4.8:
            score += 30
        elif social.nota_media >= 4.5:
            score += 20
        elif social.nota_media >= 4.0:
            score += 10
        elif social.nota_media > 0:
            score += 5
        else:
            feedback.append("Sem nota")
        
        # Perguntas e respostas
        if social.perguntas > 0:
            score += 15  # Engajamento
        if social.respostas > 0:
            score += 15
        
        return {
            "score": min(score, 100),
            "reviews": social.avaliacoes,
            "rating": social.nota_media,
            "feedback": feedback
        }
    
    def _score_badges(self, listing: ListingNormalized) -> Dict[str, Any]:
        """Avaliar selos"""
        
        badges = listing.badges
        score = 0
        feedback = []
        
        if badges.frete_gratis:
            score += 30
        else:
            feedback.append("Adicionar frete grátis")
        
        if badges.full:
            score += 25
        else:
            feedback.append("Considere fulfillment full")
        
        if badges.oficial:
            score += 25
        elif badges.premium:
            score += 15
        
        if badges.novo:
            score += 10
        
        if badges.melhorei_preco:
            score += 10
        
        return {
            "score": min(score, 100),
            "badges_count": sum([
                badges.frete_gratis,
                badges.full,
                badges.oficial,
                badges.premium,
                badges.novo
            ]),
            "feedback": feedback
        }
    
    def _score_text(self, listing: ListingNormalized) -> Dict[str, Any]:
        """Avaliar texto do anúncio"""
        
        text = listing.text_blocks
        score = 0
        feedback = []
        
        # Bullets
        bullet_count = len(text.bullets)
        if bullet_count >= 5:
            score += 40
        elif bullet_count >= 3:
            score += 25
        elif bullet_count >= 1:
            score += 10
        else:
            feedback.append("Adicionar bullets")
        
        # Descrição
        desc_length = len(text.descricao or "")
        if desc_length >= 500:
            score += 40
        elif desc_length >= 200:
            score += 25
        elif desc_length >= 50:
            score += 15
        else:
            feedback.append("Descrição muito curta")
        
        # Verificar keywords nos bullets
        if text.bullets:
            score += 20
        
        return {
            "score": min(score, 100),
            "bullet_count": bullet_count,
            "description_length": desc_length,
            "feedback": feedback
        }
    
    def _score_seller(self, listing: ListingNormalized) -> Dict[str, Any]:
        """Avaliar vendedor"""
        
        seller = listing.seller
        score = 0
        feedback = []
        
        # Reputação
        rep = seller.reputacao.value if seller.reputacao else "new"
        if rep == "gold":
            score += 40
        elif rep == "silver":
            score += 25
        elif rep == "bronze":
            score += 10
        else:
            feedback.append("Vendedor novo")
        
        # Tempo de mercado
        if seller.tempo_mercado_meses:
            if seller.tempo_mercado_meses >= 24:
                score += 30
            elif seller.tempo_mercado_meses >= 12:
                score += 20
            elif seller.tempo_mercado_meses >= 6:
                score += 10
        else:
            feedback.append("Sem histórico")
        
        # Métricas
        if seller.metricas:
            if seller.metricas.vendas_12m and seller.metricas.vendas_12m >= 100:
                score += 20
        
        # Loja oficial
        if seller.tiene_tienda_oficial:
            score += 10
        
        return {
            "score": min(score, 100),
            "reputation": rep,
            "feedback": feedback
        }
    
    def _generate_suggestions(self, factors: Dict) -> List[str]:
        """Gerar sugestões"""
        
        suggestions = []
        
        for factor_name, factor_data in factors.items():
            if factor_data["score"] < 60:
                for feedback in factor_data.get("feedback", []):
                    suggestions.append(f"[{factor_name.upper()}] {feedback}")
        
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
