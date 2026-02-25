"""
Motor de Scoring — SEO para Marketplaces.

Avalia um anúncio em 5 dimensões do SEO interno de marketplace:
  1. Título (comprimento, keywords, formatação)
  2. Atributos (completude)
  3. Conteúdo textual (bullets, descrição)
  4. Keywords (termos no título vs top concorrentes)
  5. Regras por marketplace (limites, proibições)

Score final: 0–100 → Ruim (<40) | Regular (40–64) | Bom (65–79) | Excelente (≥80)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import re

from api.src.types.listing import ListingNormalized, Marketplace, ScoreBreakdown


# ── Regras por Marketplace ─────────────────────────────────────

MARKETPLACE_RULES = {
    Marketplace.MERCADO_LIVRE: {
        "title_max": 60,
        "title_min": 40,
        "title_recommended": 55,
        "bullets_max": 6,
        "bullets_ideal": 5,
        "description_min_chars": 300,
        "attributes_required": [
            "cor", "material", "largura_cm", "profundidade_cm", "altura_cm",
        ],
        "forbidden_terms": [
            "grátis", "promoção", "oferta", "melhor preço", "barato",
            "frete grátis",  # não pode no título no ML
            "!", "?", "$",
        ],
    },
    Marketplace.MAGALU: {
        "title_max": 100,
        "title_min": 30,
        "title_recommended": 70,
        "bullets_max": 10,
        "bullets_ideal": 6,
        "description_min_chars": 200,
        "attributes_required": ["cor", "material", "largura_cm", "altura_cm"],
        "forbidden_terms": ["!", "?"],
    },
}

DEFAULT_RULES = MARKETPLACE_RULES[Marketplace.MERCADO_LIVRE]


@dataclass
class SEOScoreResult:
    score: float
    label: str
    breakdown: dict = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)

    def to_schema(self) -> ScoreBreakdown:
        return ScoreBreakdown(
            score=self.score,
            label=self.label,
            details=self.breakdown,
            suggestions=self.suggestions,
        )


class SEOScorer:
    """
    Calcula o score SEO de um anúncio.
    Pode ser usado standalone ou passando lista de concorrentes
    para comparar termos.
    """

    def score(
        self,
        listing: ListingNormalized,
        competitors: Optional[list[ListingNormalized]] = None,
    ) -> SEOScoreResult:
        rules = MARKETPLACE_RULES.get(listing.marketplace, DEFAULT_RULES)
        competitors = competitors or []

        s_title, t_suggestions = self._score_title(listing, rules)
        s_attrs, a_suggestions = self._score_attributes(listing, rules)
        s_content, c_suggestions = self._score_content(listing, rules)
        s_keywords, k_suggestions = self._score_keywords(listing, competitors)
        s_rules, r_suggestions = self._score_rules_compliance(listing, rules)

        # Pesos: título (35%) + atributos (20%) + conteúdo (15%) + keywords (20%) + compliance (10%)
        total = (
            s_title * 0.35
            + s_attrs * 0.20
            + s_content * 0.15
            + s_keywords * 0.20
            + s_rules * 0.10
        )
        total = round(total, 1)

        suggestions = t_suggestions + a_suggestions + c_suggestions + k_suggestions + r_suggestions

        return SEOScoreResult(
            score=total,
            label=self._label(total),
            breakdown={
                "titulo": round(s_title, 1),
                "atributos": round(s_attrs, 1),
                "conteudo": round(s_content, 1),
                "keywords": round(s_keywords, 1),
                "compliance": round(s_rules, 1),
            },
            suggestions=suggestions[:8],  # top 8 ações
        )

    # ── Título ────────────────────────────────────────────────

    def _score_title(self, listing: ListingNormalized, rules: dict) -> tuple[float, list[str]]:
        title = listing.title
        length = len(title)
        suggestions: list[str] = []
        score = 100.0

        max_len = rules["title_max"]
        min_len = rules["title_min"]
        recommended = rules["title_recommended"]

        if length > max_len:
            excess = length - max_len
            score -= min(40, excess * 2)
            suggestions.append(
                f"Título longo ({length} chars) — corte para ≤ {max_len}. "
                f"Remova termos redundantes no final."
            )
        elif length < min_len:
            score -= 25
            suggestions.append(
                f"Título curto ({length} chars) — expanda para {min_len}–{recommended} chars "
                f"incluindo marca, modelo e principal atributo."
            )
        elif length < recommended:
            score -= 10
            suggestions.append(
                f"Título pode crescer mais ({length} chars). "
                f"Ideal: {recommended} chars para melhor indexação."
            )

        # Primeira palavra deve ser substantivo/nome do produto (não artigo)
        first_word = title.split()[0].lower() if title.split() else ""
        if first_word in ("o", "a", "os", "as", "um", "uma"):
            score -= 10
            suggestions.append(
                f'Título começa com artigo "{first_word}". '
                "Inicie com o nome do produto (ex: 'Sofá Retrátil 3 Lugares')."
            )

        # Sem letras maiúsculas excessivas (ALL CAPS)
        words = title.split()
        all_caps = sum(1 for w in words if w.isupper() and len(w) > 2)
        if all_caps > 2:
            score -= 10
            suggestions.append(
                f"{all_caps} palavras em MAIÚSCULAS. Use Title Case — apenas primeira letra maiúscula."
            )

        return max(0.0, score), suggestions

    # ── Atributos ─────────────────────────────────────────────

    def _score_attributes(self, listing: ListingNormalized, rules: dict) -> tuple[float, list[str]]:
        required = rules.get("attributes_required", [])
        suggestions: list[str] = []
        attrs = listing.attributes

        missing = []
        for attr in required:
            val = getattr(attrs, attr, None)
            if val is None:
                missing.append(attr)

        pct_missing = len(missing) / max(len(required), 1)
        score = round((1 - pct_missing) * 100, 1)

        if missing:
            labels = {
                "cor": "Cor",
                "material": "Material",
                "largura_cm": "Largura (cm)",
                "profundidade_cm": "Profundidade (cm)",
                "altura_cm": "Altura (cm)",
                "peso_kg": "Peso (kg)",
            }
            missing_names = [labels.get(m, m) for m in missing]
            suggestions.append(
                f"Atributos obrigatórios ausentes: {', '.join(missing_names)}. "
                "Preencha na ficha técnica do anúncio."
            )

        return max(0.0, score), suggestions

    # ── Conteúdo textual ──────────────────────────────────────

    def _score_content(self, listing: ListingNormalized, rules: dict) -> tuple[float, list[str]]:
        suggestions: list[str] = []
        score = 100.0

        bullets = listing.text_blocks.bullets
        descricao = listing.text_blocks.descricao or ""
        ideal_bullets = rules.get("bullets_ideal", 5)
        desc_min = rules.get("description_min_chars", 300)

        if not bullets:
            score -= 35
            suggestions.append(
                f"Sem bullets/tópicos. Adicione {ideal_bullets} tópicos destacando diferenciais "
                "(ex: material, dimensões, garantia, uso)."
            )
        elif len(bullets) < ideal_bullets:
            diff = ideal_bullets - len(bullets)
            score -= diff * 7
            suggestions.append(
                f"Apenas {len(bullets)} bullet(s). Adicione mais {diff} para atingir {ideal_bullets}."
            )

        if not descricao:
            score -= 30
            suggestions.append(
                "Sem descrição. Escreva pelo menos 300 chars com especificações técnicas, "
                "uso, cuidados e benefícios do produto."
            )
        elif len(descricao) < desc_min:
            score -= 15
            suggestions.append(
                f"Descrição curta ({len(descricao)} chars). "
                f"Expanda para ao menos {desc_min} chars."
            )

        return max(0.0, score), suggestions

    # ── Keywords vs concorrentes ───────────────────────────────

    def _score_keywords(
        self,
        listing: ListingNormalized,
        competitors: list[ListingNormalized],
    ) -> tuple[float, list[str]]:
        suggestions: list[str] = []

        if not competitors:
            return 70.0, []  # sem benchmark, score neutro

        # Termos mais frequentes nos top concorrentes
        from collections import Counter
        all_terms: list[str] = []
        for c in competitors[:20]:
            all_terms.extend(c.seo_terms)
        top_terms = {t for t, _ in Counter(all_terms).most_common(15)}

        my_title_lower = listing.title.lower()
        matched = sum(1 for t in top_terms if t in my_title_lower)
        score = round(matched / max(len(top_terms), 1) * 100, 1)

        missing_kw = [t for t in top_terms if t not in my_title_lower]
        if missing_kw:
            suggestions.append(
                f"Termos frequentes nos concorrentes ausentes no seu título: "
                f"{', '.join(list(missing_kw)[:5])}. Considere incluir os mais relevantes."
            )

        return min(100.0, score), suggestions

    # ── Compliance (regras do marketplace) ────────────────────

    def _score_rules_compliance(self, listing: ListingNormalized, rules: dict) -> tuple[float, list[str]]:
        suggestions: list[str] = []
        score = 100.0
        forbidden = rules.get("forbidden_terms", [])
        title_lower = listing.title.lower()

        found_forbidden = [f for f in forbidden if f in title_lower]
        if found_forbidden:
            score -= len(found_forbidden) * 20
            suggestions.append(
                f"Termos proibidos no título: {', '.join(found_forbidden)}. "
                "Remova para evitar penalização ou remoção do anúncio."
            )

        return max(0.0, score), suggestions

    # ── Label ─────────────────────────────────────────────────

    @staticmethod
    def _label(score: float) -> str:
        if score >= 80:
            return "Excelente"
        if score >= 65:
            return "Bom"
        if score >= 40:
            return "Regular"
        return "Ruim"