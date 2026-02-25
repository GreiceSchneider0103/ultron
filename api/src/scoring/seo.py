"""
Motor de Scoring - SEO
"""

from typing import List, Dict, Any
from api.src.types.listing import ListingNormalized


class SEOScorer:
    """
    Calcula score de SEO para anúncios.
    
    Critérios avaliados:
    - Título: palavras-chave relevantes
    - Comprimento do título
    - Atributos preenchidos
    - Imagens com boa qualidade
    """
    
    def __init__(self):
        self.max_title_length = 60
        self.min_keywords_in_title = 3
        self.min_attributes = 3
    
    def score(
        self,
        listing: ListingNormalized,
        competitors: List[ListingNormalized]
    ) -> Dict[str, Any]:
        """
        Calcular score de SEO.
        
        Args:
            listing: Anúncio a ser avaliado
            competitors: Lista de concorrentes para comparação
            
        Returns:
            Dict com:
                - score: float (0-100)
                - factors: dict com fatores individuais
                - suggestions: list de sugestões
        """
        
        factors = {}
        
        # 1. Score do título
        title_score = self._score_title(listing, competitors)
        factors["title"] = title_score
        
        # 2. Score de palavras-chave
        keywords_score = self._score_keywords(listing, competitors)
        factors["keywords"] = keywords_score
        
        # 3. Score de atributos
        attributes_score = self._score_attributes(listing)
        factors["attributes"] = attributes_score
        
        # 4. Score de mídia
        media_score = self._score_media(listing)
        factors["media"] = media_score
        
        # Score final (média ponderada)
        weights = {
            "title": 0.30,
            "keywords": 0.30,
            "attributes": 0.25,
            "media": 0.15
        }
        
        final_score = sum(
            factors[k]["score"] * weights[k]
            for k in weights
        )
        
        # Gerar sugestões
        suggestions = self._generate_suggestions(factors)
        
        return {
            "score": round(final_score, 1),
            "factors": factors,
            "suggestions": suggestions,
            "grade": self._get_grade(final_score)
        }
    
    def _score_title(
        self,
        listing: ListingNormalized,
        competitors: List[ListingNormalized]
    ) -> Dict[str, Any]:
        """Avaliar qualidade do título"""
        
        title = listing.title
        length = len(title)
        
        score = 0
        feedback = []
        
        # Comprimento ideal (45-60 caracteres)
        if 45 <= length <= 60:
            score += 50
        elif 35 <= length < 45 or 60 < length <= 65:
            score += 30
        elif length < 35:
            score += 10
            feedback.append("Título muito curto")
        else:
            score += 10
            feedback.append("Título muito longo")
        
        # Verificar se tem termos relevantes
        if competitors:
            # Pegar top termos dos concorrentes
            top_terms = []
            for comp in competitors[:10]:
                top_terms.extend(comp.seo_terms)
            
            # Contar termos do título que aparecem nos concorrentes
            title_terms = set(listing.seo_terms)
            matching = len(title_terms.intersection(set(top_terms)))
            
            if matching >= 3:
                score += 50
            elif matching >= 1:
                score += 25
            else:
                feedback.append("Título sem palavras-chave relevantes")
        else:
            score += 25  # Sem concorrentes para comparar
        
        return {
            "score": min(score, 100),
            "length": length,
            "feedback": feedback
        }
    
    def _score_keywords(
        self,
        listing: ListingNormalized,
        competitors: List[ListingNormalized]
    ) -> Dict[str, Any]:
        """Avaliar relevância de palavras-chave"""
        
        keywords = listing.seo_terms
        keyword_count = len(keywords)
        
        score = 0
        feedback = []
        
        # Quantidade de keywords
        if keyword_count >= 5:
            score += 50
        elif keyword_count >= 3:
            score += 35
        elif keyword_count >= 1:
            score += 20
        else:
            score += 0
            feedback.append("Nenhuma palavra-chave identificada")
        
        # Verificar se keywords estão no título
        title_lower = listing.title.lower()
        keywords_in_title = sum(1 for kw in keywords if kw.lower() in title_lower)
        
        if keywords_in_title >= keyword_count * 0.7:
            score += 50
        elif keywords_in_title > 0:
            score += 25
            feedback.append("Algunas keywords fora do título")
        else:
            feedback.append("Keywords não encontradas no título")
        
        return {
            "score": min(score, 100),
            "keyword_count": keyword_count,
            "keywords_in_title": keywords_in_title,
            "feedback": feedback
        }
    
    def _score_attributes(self, listing: ListingNormalized) -> Dict[str, Any]:
        """Avaliar completude dos atributos"""
        
        attrs = listing.attributes
        filled_attrs = []
        
        # Contar atributos preenchidos
        fields = [
            attrs.cor, attrs.material, attrs.tecido,
            attrs.largura, attrs.profundidade, attrs.altura,
            attrs.peso, attrs.tipo_sofa, attrs.numero_lugares
        ]
        
        filled_count = sum(1 for f in fields if f is not None)
        
        score = min(filled_count * 15, 100)  # 7+ atributos = 100
        
        feedback = []
        if filled_count < 3:
            feedback.append("Poucos atributos preenchidos")
        
        # Sugerir atributos importantes para móveis
        important = []
        if not attrs.largura:
            important.append("largura")
        if not attrs.profundidade:
            important.append("profundidade")
        if not attrs.altura:
            important.append("altura")
        if not attrs.tecido:
            important.append("tecido")
        
        if important:
            feedback.append(f"Adicionar: {', '.join(important)}")
        
        return {
            "score": score,
            "filled_count": filled_count,
            "total_fields": len(fields),
            "feedback": feedback
        }
    
    def _score_media(self, listing: ListingNormalized) -> Dict[str, Any]:
        """Avaliar qualidade da mídia"""
        
        media = listing.media
        image_count = len([m for m in media if m.tipo == "foto"])
        
        score = 0
        feedback = []
        
        # Quantidade de imagens
        if image_count >= 8:
            score += 60
        elif image_count >= 5:
            score += 45
        elif image_count >= 3:
            score += 30
        elif image_count >= 1:
            score += 15
        else:
            feedback.append("Sem imagens")
        
        # Tem capa
        has_capa = any(m.is_capa for m in media)
        if has_capa:
            score += 20
        else:
            feedback.append("Sem imagem de capa definida")
        
        # Tem vídeo
        has_video = any(m.tipo == "video" for m in media)
        if has_video:
            score += 20
        else:
            feedback.append("Considere adicionar vídeo")
        
        return {
            "score": min(score, 100),
            "image_count": image_count,
            "has_video": has_video,
            "feedback": feedback
        }
    
    def _generate_suggestions(self, factors: Dict) -> List[str]:
        """Gerar lista de sugestões baseadas nos fatores"""
        
        suggestions = []
        
        for factor_name, factor_data in factors.items():
            if factor_data["score"] < 60:
                for feedback in factor_data.get("feedback", []):
                    suggestions.append(f"[{factor_name.upper()}] {feedback}")
        
        return suggestions
    
    def _get_grade(self, score: float) -> str:
        """Converter score em nota"""
        
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
