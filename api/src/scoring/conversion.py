"""
Motor de Scoring — Conversão e Competitividade.

ConversionScorer: avalia o potencial do anúncio de converter visitantes em compradores.
  - Prova social (avaliações, nota)
  - Mídia (quantidade e qualidade de imagens)
  - Badges (frete grátis, FULL, parcelamento)
  - Preço vs concorrentes

CompetitivenessScorer: avalia posição relativa vs mercado.
  - Preço relativo
  - Seller reputation
  - FULL vs concorrentes
  - Diferencial de conteúdo
"""
from __future__ import annotations

from typing import Optional
from api.src.types.listing import ListingNormalized, ScoreBreakdown


# ── Conversão ─────────────────────────────────────────────────

class ConversionScorer:

    def score(
        self,
        listing: ListingNormalized,
        competitors: Optional[list[ListingNormalized]] = None,
    ) -> ScoreBreakdown:
        competitors = competitors or []

        s_social, sug_social = self._score_social(listing, competitors)
        s_media, sug_media = self._score_media(listing)
        s_badges, sug_badges = self._score_badges(listing, competitors)
        s_price, sug_price = self._score_price(listing, competitors)

        # Pesos: mídia (30%) + social (30%) + badges (25%) + preço (15%)
        total = round(
            s_media * 0.30
            + s_social * 0.30
            + s_badges * 0.25
            + s_price * 0.15,
            1,
        )

        suggestions = sug_media + sug_social + sug_badges + sug_price

        return ScoreBreakdown(
            score=total,
            label=self._label(total),
            details={
                "prova_social": round(s_social, 1),
                "midia": round(s_media, 1),
                "badges": round(s_badges, 1),
                "preco": round(s_price, 1),
            },
            suggestions=suggestions[:6],
        )

    # ── Social Proof ──────────────────────────────────────────

    def _score_social(
        self,
        listing: ListingNormalized,
        competitors: list[ListingNormalized],
    ) -> tuple[float, list[str]]:
        sp = listing.social_proof
        suggestions: list[str] = []
        score = 0.0

        # Avaliações: 0→30 pontos
        rev = sp.avaliacoes_total
        if rev >= 100:
            score += 30
        elif rev >= 50:
            score += 22
        elif rev >= 20:
            score += 15
        elif rev >= 5:
            score += 8
        else:
            score += 0
            suggestions.append(
                f"Apenas {rev} avaliação(ões). Incentive clientes a avaliar "
                "com mensagens pós-venda ou cupom."
            )

        # Nota: 0→40 pontos
        rating = sp.nota_media
        if rating >= 4.7:
            score += 40
        elif rating >= 4.3:
            score += 30
        elif rating >= 3.8:
            score += 18
        elif rating > 0:
            score += 8
            suggestions.append(
                f"Nota {rating:.1f} abaixo da média. Investigue reclamações e melhore "
                "descrição/imagens para reduzir expectativa vs realidade."
            )

        # Vendas estimadas vs concorrentes: 0→30 pontos
        my_sales = sp.vendas_estimadas or 0
        if competitors:
            avg_sales = sum(
                (c.social_proof.vendas_estimadas or 0) for c in competitors
            ) / max(len(competitors), 1)
            ratio = my_sales / max(avg_sales, 1)
            score += min(30, ratio * 30)
        else:
            score += 15  # neutro sem benchmark

        return min(100.0, score), suggestions

    # ── Mídia ─────────────────────────────────────────────────

    def _score_media(self, listing: ListingNormalized) -> tuple[float, list[str]]:
        suggestions: list[str] = []
        count = listing.media_count
        score = 0.0

        if count >= 10:
            score = 100
        elif count >= 7:
            score = 80
        elif count >= 5:
            score = 60
            suggestions.append(
                f"{count} imagens — adicione mais fotos (ângulos, detalhes, ambientação) "
                "para atingir 7–10 fotos e aumentar confiança do comprador."
            )
        elif count >= 3:
            score = 35
            suggestions.append(
                f"Apenas {count} imagens. O ideal é 7–10 fotos de alta resolução "
                "(frente, lateral, detalhe de tecido, foto ambientada, dimensões)."
            )
        else:
            score = 10
            suggestions.append(
                "Poucas ou nenhuma imagem. Anúncios com 7+ fotos convertem 3× mais. "
                "Adicione fotos profissionais imediatamente."
            )

        return score, suggestions

    # ── Badges ────────────────────────────────────────────────

    def _score_badges(
        self,
        listing: ListingNormalized,
        competitors: list[ListingNormalized],
    ) -> tuple[float, list[str]]:
        suggestions: list[str] = []
        score = 0.0

        if listing.badges.frete_gratis:
            score += 40
        else:
            # Verifica se maioria dos concorrentes tem frete grátis
            if competitors:
                free_pct = sum(
                    1 for c in competitors if c.badges.frete_gratis
                ) / len(competitors)
                if free_pct > 0.5:
                    suggestions.append(
                        f"{int(free_pct*100)}% dos concorrentes oferecem frete grátis. "
                        "Avaliar absorver custo no preço ou negociar com transportadora."
                    )

        if listing.badges.full:
            score += 30
        elif listing.badges.frete_gratis:
            pass  # já pontuou acima
        else:
            if competitors and any(c.badges.full for c in competitors):
                suggestions.append(
                    "Concorrentes com FULL/entrega rápida. Considere enviar estoque "
                    "para o fulfillment do marketplace."
                )

        if listing.badges.parcelamento_sem_juros:
            score += 20
        else:
            suggestions.append(
                "Ofereça parcelamento sem juros (6–12x). Aumenta ticket percebido "
                "e reduz abandono por preço."
            )

        score += 10  # base

        return min(100.0, score), suggestions

    # ── Preço ─────────────────────────────────────────────────

    def _score_price(
        self,
        listing: ListingNormalized,
        competitors: list[ListingNormalized],
    ) -> tuple[float, list[str]]:
        suggestions: list[str] = []
        if not competitors:
            return 70.0, []

        prices = [c.final_price_estimate for c in competitors if c.final_price_estimate > 0]
        if not prices:
            return 70.0, []

        avg = sum(prices) / len(prices)
        my = listing.final_price_estimate or listing.price
        ratio = my / avg if avg else 1.0

        if ratio <= 0.9:
            score = 100.0
        elif ratio <= 1.0:
            score = 85.0
        elif ratio <= 1.15:
            score = 65.0
            suggestions.append(
                f"Preço {int((ratio-1)*100)}% acima da média (R$ {avg:.0f}). "
                "Se não houver diferencial claro, considere ajustar."
            )
        elif ratio <= 1.30:
            score = 45.0
            suggestions.append(
                f"Preço {int((ratio-1)*100)}% acima da média. "
                "Destaque diferenciais (qualidade, garantia) nos bullets para justificar."
            )
        else:
            score = 20.0
            suggestions.append(
                f"Preço muito acima da média (R$ {avg:.0f}). "
                "Revise estratégia de precificação ou reposicione o produto."
            )

        return score, suggestions

    @staticmethod
    def _label(score: float) -> str:
        if score >= 80:
            return "Excelente"
        if score >= 65:
            return "Bom"
        if score >= 40:
            return "Regular"
        return "Ruim"


# ── Competitividade ───────────────────────────────────────────

class CompetitivenessScorer:

    def score(
        self,
        listing: ListingNormalized,
        competitors: list[ListingNormalized],
    ) -> ScoreBreakdown:
        if not competitors:
            return ScoreBreakdown(
                score=50.0,
                label="Regular",
                details={},
                suggestions=["Adicione concorrentes para score de competitividade."],
            )

        s_price = self._relative_price_score(listing, competitors)
        s_rep = self._reputation_score(listing)
        s_content = self._content_advantage(listing, competitors)
        s_velocity = self._sales_velocity(listing, competitors)

        total = round(
            s_price * 0.35
            + s_rep * 0.25
            + s_content * 0.25
            + s_velocity * 0.15,
            1,
        )

        return ScoreBreakdown(
            score=total,
            label=self._label(total),
            details={
                "preco_relativo": round(s_price, 1),
                "reputacao_seller": round(s_rep, 1),
                "vantagem_conteudo": round(s_content, 1),
                "velocidade_vendas": round(s_velocity, 1),
            },
            suggestions=self._gen_suggestions(listing, competitors),
        )

    def _relative_price_score(
        self, listing: ListingNormalized, competitors: list[ListingNormalized]
    ) -> float:
        prices = [c.final_price_estimate for c in competitors if c.final_price_estimate > 0]
        if not prices:
            return 50.0
        avg = sum(prices) / len(prices)
        my = listing.final_price_estimate or listing.price
        ratio = my / avg
        if ratio < 0.85:
            return 100.0
        if ratio < 1.0:
            return 80.0
        if ratio < 1.15:
            return 60.0
        if ratio < 1.3:
            return 40.0
        return 20.0

    @staticmethod
    def _reputation_score(listing: ListingNormalized) -> float:
        from api.src.types.listing import SellerReputation
        rep_scores = {
            SellerReputation.PLATINUM: 100,
            SellerReputation.GOLD: 80,
            SellerReputation.SILVER: 55,
            SellerReputation.BRONZE: 35,
            SellerReputation.NEW: 15,
            SellerReputation.UNKNOWN: 30,
        }
        return rep_scores.get(listing.seller.reputacao, 30)

    def _content_advantage(
        self, listing: ListingNormalized, competitors: list[ListingNormalized]
    ) -> float:
        avg_media = sum(c.media_count for c in competitors) / len(competitors)
        avg_bullets = sum(len(c.text_blocks.bullets) for c in competitors) / len(competitors)
        my_media_score = min(100, listing.media_count / max(avg_media, 1) * 100)
        my_bullet_score = min(100, len(listing.text_blocks.bullets) / max(avg_bullets, 1) * 100)
        return (my_media_score + my_bullet_score) / 2

    def _sales_velocity(
        self, listing: ListingNormalized, competitors: list[ListingNormalized]
    ) -> float:
        my = listing.social_proof.vendas_estimadas or 0
        avg = sum(
            (c.social_proof.vendas_estimadas or 0) for c in competitors
        ) / max(len(competitors), 1)
        if avg == 0:
            return 50.0
        return min(100, my / avg * 100)

    @staticmethod
    def _gen_suggestions(
        listing: ListingNormalized, competitors: list[ListingNormalized]
    ) -> list[str]:
        sug = []
        full_competitors = sum(1 for c in competitors if c.badges.full)
        if full_competitors > len(competitors) * 0.4 and not listing.badges.full:
            sug.append(
                f"{full_competitors} concorrentes usam FULL/fulfillment. "
                "Considere enviar estoque para o CD do marketplace."
            )
        platinum_count = sum(
            1 for c in competitors
            if c.seller.reputacao.value == "platinum"
        )
        if platinum_count > len(competitors) * 0.3:
            sug.append(
                f"{platinum_count} concorrentes são vendedores Platinum/Top. "
                "Foque em conteúdo e preço para compensar reputação."
            )
        return sug[:4]

    @staticmethod
    def _label(score: float) -> str:
        if score >= 80:
            return "Líder"
        if score >= 65:
            return "Competitivo"
        if score >= 40:
            return "Regular"
        return "Fraco"