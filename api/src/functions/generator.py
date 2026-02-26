"""
functions/generator.py — Gerador de conteúdo com IA.
COLOQUE EM: api/src/functions/generator.py
Crie também: api/src/functions/__init__.py (arquivo vazio)

Funções exportadas:
  generate_titles()           → list[str]
  generate_bullets()          → list[str]
  generate_description()      → str
  generate_full_listing()     → dict  (anúncio completo do zero)
  generate_audit_recommendations() → dict (10 ações priorizadas)
"""
from __future__ import annotations

import json
import re
from typing import Optional

import structlog

from api.src.config import settings

log = structlog.get_logger()

# ── System prompt base ────────────────────────────────────────

SYSTEM_SEO = """Você é especialista em SEO de marketplaces brasileiros (Mercado Livre e Magalu).
Gere conteúdo que maximize visibilidade orgânica e taxa de conversão.

Regras fixas:
- Títulos ML: máximo 60 caracteres, sem artigo no início, sem: !, ?, grátis, promoção, frete grátis
- Títulos Magalu: máximo 100 caracteres
- Bullets: concisos, iniciar com substantivo ou verbo no imperativo
- Descrição: rich text com specs técnicas + benefícios (mín 400 chars)
- Português brasileiro formal
- Nunca invente especificações não fornecidas
- Responda APENAS com JSON válido, sem markdown nem explicações."""


# ── LLM caller ────────────────────────────────────────────────

async def _call_llm(user_prompt: str) -> str:
    provider = settings.DEFAULT_AI_PROVIDER
    if provider == "anthropic":
        return await _anthropic(user_prompt)
    if provider == "gemini":
        return await _gemini(user_prompt)
    return await _openai(user_prompt)


async def _openai(prompt: str) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    resp = await client.chat.completions.create(
        model=settings.DEFAULT_AI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_SEO},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or "{}"


async def _anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    msg = await client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        system=SYSTEM_SEO,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return msg.content[0].text if msg.content else "{}"


async def _gemini(prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model_name = settings.DEFAULT_AI_MODEL or "gemini-1.5-flash"
    if model_name.startswith(("gpt-", "claude")):
        model_name = "gemini-1.5-flash"
    model = genai.GenerativeModel(model_name=model_name)
    response = await model.generate_content_async(
        [SYSTEM_SEO, prompt],
        generation_config={"temperature": 0.4},
    )
    text = getattr(response, "text", None)
    return text or "{}"


def _parse(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    log.error("json_parse_failed", raw=raw[:200])
    return {}


def _ctx(
    keyword: str,
    marketplace: str,
    attributes: Optional[dict] = None,
    top_terms: Optional[list[str]] = None,
    price_range: Optional[dict] = None,
) -> str:
    lines = [f"Produto: {keyword}", f"Marketplace: {marketplace}"]
    if attributes:
        lines.append(f"Atributos: {json.dumps(attributes, ensure_ascii=False)}")
    if top_terms:
        lines.append(f"Top termos dos concorrentes: {', '.join(top_terms[:15])}")
    if price_range:
        lines.append(
            f"Faixa de preço: R$ {price_range.get('min',0):.0f}–"
            f"R$ {price_range.get('max',0):.0f} (média R$ {price_range.get('avg',0):.0f})"
        )
    return "\n".join(lines)


# ── Funções públicas ──────────────────────────────────────────

async def generate_titles(
    keyword: str,
    marketplace: str = "mercado_livre",
    attributes: Optional[dict] = None,
    top_terms: Optional[list[str]] = None,
    n_variants: int = 5,
) -> list[str]:
    max_c = 60 if marketplace == "mercado_livre" else 100
    ctx = _ctx(keyword, marketplace, attributes, top_terms)
    proibido = (
        "Proibido no título: !, ?, grátis, promoção, oferta, frete grátis"
        if marketplace == "mercado_livre" else "Evite pontuação excessiva"
    )
    prompt = f"""{ctx}

Gere {n_variants} variantes de título otimizado.
- Máximo {max_c} caracteres
- Não comece com artigo (o/a/os/as/um/uma)
- Inclua os termos dos concorrentes mais relevantes
- {proibido}
- Varie a estrutura entre as variantes

JSON: {{"titulos": ["...", ...]}}"""

    data = _parse(await _call_llm(prompt))
    return data.get("titulos", [])


async def generate_bullets(
    keyword: str,
    marketplace: str = "mercado_livre",
    attributes: Optional[dict] = None,
    n_bullets: int = 5,
) -> list[str]:
    ctx = _ctx(keyword, marketplace, attributes)
    prompt = f"""{ctx}

Gere {n_bullets} bullets de destaque para o anúncio.
- Cada bullet: 1 frase (máx 120 chars)
- Inicie com substantivo ou verbo no imperativo
- Destaque benefícios reais (evite "excelente qualidade")
- Inclua pelo menos 1 bullet sobre dimensões e 1 sobre material
- Se houver garantia nos atributos, inclua 1 bullet sobre ela

JSON: {{"bullets": ["...", ...]}}"""

    data = _parse(await _call_llm(prompt))
    return data.get("bullets", [])


async def generate_description(
    keyword: str,
    marketplace: str = "mercado_livre",
    attributes: Optional[dict] = None,
    top_terms: Optional[list[str]] = None,
) -> str:
    ctx = _ctx(keyword, marketplace, attributes, top_terms)
    min_c = 400 if marketplace == "mercado_livre" else 300
    prompt = f"""{ctx}

Escreva descrição completa para este anúncio.
- Mínimo {min_c} caracteres
- Estrutura: [Apresentação] → [Especificações técnicas] → [Benefícios] → [Cuidados/garantia]
- Use os termos dos concorrentes naturalmente (SEO)
- Sem markdown — texto corrido com parágrafos separados por \n\n

JSON: {{"descricao": "texto aqui"}}"""

    data = _parse(await _call_llm(prompt))
    return data.get("descricao", "")


async def generate_full_listing(
    keyword: str,
    marketplace: str = "mercado_livre",
    attributes: Optional[dict] = None,
    top_terms: Optional[list[str]] = None,
    price_range: Optional[dict] = None,
) -> dict:
    """Gera anúncio completo do zero: títulos + bullets + descrição + keywords ADS + pauta foto + preço + A/B."""
    ctx = _ctx(keyword, marketplace, attributes, top_terms, price_range)
    max_t = 60 if marketplace == "mercado_livre" else 100

    prompt = f"""{ctx}

Gere um anúncio completo. Responda em JSON:
{{
  "titulos": ["5 variantes, máx {max_t} chars cada"],
  "bullets": ["5 bullets de destaque"],
  "descricao": "descrição completa (mín 400 chars, sem markdown)",
  "keywords_ads": ["10 palavras-chave para campanhas pagas"],
  "pauta_fotografica": [
    {{"tipo": "capa", "descricao": "produto centralizado fundo branco ângulo frontal"}},
    {{"tipo": "detalhe", "descricao": "..."}},
    {{"tipo": "ambientação", "descricao": "..."}},
    {{"tipo": "dimensões", "descricao": "infográfico com medidas"}},
    {{"tipo": "variações", "descricao": "..."}}
  ],
  "sugestao_preco": {{
    "preco_entrada": 0,
    "preco_competitivo": 0,
    "preco_premium": 0,
    "justificativa": "texto curto"
  }},
  "ab_test_ideas": [
    {{"elemento": "titulo", "variante_a": "...", "variante_b": "...", "hipotese": "..."}},
    {{"elemento": "capa", "variante_a": "...", "variante_b": "...", "hipotese": "..."}}
  ]
}}"""

    return _parse(await _call_llm(prompt))


async def generate_audit_recommendations(
    listing_data: Optional[dict] = None,
    market_data: Optional[dict] = None,
    seo_score: float = 0.0,
    conversion_score: float = 0.0,
    **kwargs,
) -> dict:
    """Gera as 10 próximas ações priorizadas."""
    # Compat with orchestrator.agent canonical call
    if listing_data is None and "listing" in kwargs:
        listing_obj = kwargs["listing"]
        listing_data = (
            listing_obj.model_dump(exclude_none=True)
            if hasattr(listing_obj, "model_dump")
            else dict(listing_obj)
        )
    if market_data is None:
        competitors = kwargs.get("competitors", [])
        top_seo_terms = kwargs.get("top_seo_terms", [])
        market_data = {
            "competitors_count": len(competitors),
            "top_seo_terms": top_seo_terms,
        }

    prompt = f"""Meu anúncio: {json.dumps(listing_data, ensure_ascii=False)}
Dados do mercado: {json.dumps(market_data, ensure_ascii=False)}
Score SEO: {seo_score}/100 | Score Conversão: {conversion_score}/100

Gere as 10 próximas ações priorizadas para melhorar este anúncio.
JSON:
{{
  "acoes": [
    {{
      "prioridade": 1,
      "categoria": "SEO|Conteúdo|Preço|Logística|Mídia|Ads",
      "acao": "descrição clara e acionável",
      "impacto_esperado": "ex: +15% cliques orgânicos",
      "esforco": "baixo|médio|alto",
      "prazo": "imediato|1 semana|1 mês"
    }}
  ],
  "alertas": ["alerta crítico 1", "alerta crítico 2"],
  "oportunidade_principal": "frase de 1 linha com a maior oportunidade detectada"
}}"""

    return _parse(await _call_llm(prompt))
