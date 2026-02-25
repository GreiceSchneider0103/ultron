"""
Ultron API — FastAPI principal.

Endpoints:
  GET  /health                  → Status e configuração
  POST /research                → Pesquisa de mercado
  POST /audit                   → Auditoria de anúncio
  POST /create-listing          → Gerar anúncio do zero
  POST /compare                 → Comparar dois anúncios
  POST /generate/titles         → Gerar títulos
  POST /generate/bullets        → Gerar bullets
  POST /generate/description    → Gerar descrição
  GET  /docs                    → Swagger UI (OpenAPI)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional
import structlog

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.src.config import get_settings, Settings
from api.src.orchestrator.agent import MarketAgent

log = structlog.get_logger()


# ── Lifecycle ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    log.info(
        "ultron_startup",
        environment=cfg.environment,
        ai_provider=cfg.default_ai_provider,
        ai_ready=cfg.check_ai_configured(),
        ml_ready=cfg.check_ml_configured(),
    )
    yield
    log.info("ultron_shutdown")


# ── App ───────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="Ultron — Agente de Mercado/SEO/ADS",
    description=(
        "API do agente inteligente para pesquisa de mercado, "
        "auditoria de anúncios, scoring SEO e geração de conteúdo "
        "para Mercado Livre e Magalu."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Dependency ────────────────────────────────────────────────

def get_agent() -> MarketAgent:
    return MarketAgent()


# ── Request / Response Schemas ────────────────────────────────

class ResearchRequest(BaseModel):
    keyword: str = Field(..., min_length=2, example="sofá retrátil 3 lugares")
    marketplace: str = Field("mercado_livre", example="mercado_livre")
    limit: int = Field(50, ge=5, le=100)


class AuditRequest(BaseModel):
    listing_id: str = Field(..., example="MLB1234567890")
    marketplace: str = Field("mercado_livre")
    keyword: Optional[str] = Field(None, example="sofá retrátil")


class CreateListingRequest(BaseModel):
    keyword: str = Field(..., min_length=2, example="sofá retrátil 3 lugares")
    marketplace: str = Field("mercado_livre")
    attributes: Optional[dict] = Field(
        None,
        example={
            "cor": "cinza",
            "material": "linho",
            "largura_cm": 220,
            "altura_cm": 85,
            "profundidade_cm": 95,
            "numero_lugares": 3,
        },
    )


class CompareRequest(BaseModel):
    listing_id_a: str
    listing_id_b: str
    marketplace: str = "mercado_livre"


class GenerateTitlesRequest(BaseModel):
    keyword: str
    marketplace: str = "mercado_livre"
    attributes: Optional[dict] = None
    top_terms: Optional[list[str]] = None
    n_variants: int = Field(5, ge=1, le=10)


class GenerateBulletsRequest(BaseModel):
    keyword: str
    marketplace: str = "mercado_livre"
    attributes: Optional[dict] = None
    n_bullets: int = Field(5, ge=3, le=10)


class GenerateDescriptionRequest(BaseModel):
    keyword: str
    marketplace: str = "mercado_livre"
    attributes: Optional[dict] = None
    top_terms: Optional[list[str]] = None


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
async def health(cfg: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": cfg.environment,
        "ai_provider": cfg.default_ai_provider,
        "ai_configured": cfg.check_ai_configured(),
        "ml_configured": cfg.check_ml_configured(),
        "connectors_available": ["mercado_livre", "magalu"],
    }


@app.post("/research", tags=["Mercado"])
async def research_market(
    req: ResearchRequest,
    agent: MarketAgent = Depends(get_agent),
):
    """
    **Pesquisa de mercado completa.**

    Coleta os top anúncios do marketplace, normaliza, agrega métricas:
    - Faixa de preço (min/max/avg/median)
    - Top 30 termos SEO dos concorrentes
    - Resumo de concorrentes (badges, frete, mídia)
    - Gaps de mercado detectados automaticamente
    """
    try:
        result = await agent.research_market(
            keyword=req.keyword,
            marketplace=req.marketplace,
            limit=req.limit,
        )
        # Serializa sem os listings completos para resposta leve
        return {
            "keyword": result.keyword,
            "marketplace": result.marketplace,
            "total_collected": result.total_collected,
            "price_range": result.price_range,
            "top_seo_terms": result.top_seo_terms,
            "competitor_summary": result.competitor_summary,
            "gaps": result.gaps,
            "research_at": result.research_at.isoformat(),
        }
    except Exception as exc:
        log.error("research_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/audit", tags=["Auditoria"])
async def audit_listing(
    req: AuditRequest,
    agent: MarketAgent = Depends(get_agent),
):
    """
    **Auditoria completa de um anúncio.**

    - Score SEO (0–100): título, atributos, conteúdo, keywords, compliance
    - Score Conversão (0–100): mídia, social proof, badges, preço
    - Score Competitividade (0–100): posição relativa no mercado
    - Score geral ponderado
    - Top 10 ações recomendadas (com IA, se configurada)
    - 5 variantes de título geradas
    """
    try:
        result = await agent.audit_listing(
            listing_id=req.listing_id,
            marketplace=req.marketplace,
            keyword=req.keyword,
        )
        return result.model_dump()
    except Exception as exc:
        log.error("audit_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/create-listing", tags=["Geração"])
async def create_listing(
    req: CreateListingRequest,
    agent: MarketAgent = Depends(get_agent),
):
    """
    **Gera um anúncio completo do zero.**

    Retorna:
    - 5 variantes de título otimizado
    - 5 bullets de destaque
    - Descrição completa (≥400 chars)
    - 10 keywords para ADS
    - Pauta fotográfica (tipos de foto recomendados)
    - Sugestão de preço (entrada/competitivo/premium)
    - 2 ideias de teste A/B
    - Contexto de mercado (faixa de preço, gaps, termos dos concorrentes)

    **Requer IA configurada** (OPENAI_API_KEY ou ANTHROPIC_API_KEY).
    """
    try:
        result = await agent.create_listing(
            keyword=req.keyword,
            marketplace=req.marketplace,
            attributes=req.attributes,
        )
        return result
    except Exception as exc:
        log.error("create_listing_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/compare", tags=["Auditoria"])
async def compare_listings(
    req: CompareRequest,
    agent: MarketAgent = Depends(get_agent),
):
    """**Compara dois anúncios lado a lado com scores SEO e Conversão.**"""
    try:
        return await agent.compare_listings(
            listing_id_a=req.listing_id_a,
            listing_id_b=req.listing_id_b,
            marketplace=req.marketplace,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/generate/titles", tags=["Geração"])
async def generate_titles_endpoint(req: GenerateTitlesRequest):
    """**Gera N variantes de título SEO.** Requer IA configurada."""
    from api.src.functions.generator import generate_titles
    if not get_settings().check_ai_configured():
        raise HTTPException(status_code=400, detail="IA não configurada.")
    titles = await generate_titles(
        keyword=req.keyword,
        marketplace=req.marketplace,
        attributes=req.attributes,
        top_terms=req.top_terms,
        n_variants=req.n_variants,
    )
    return {"titles": titles}


@app.post("/generate/bullets", tags=["Geração"])
async def generate_bullets_endpoint(req: GenerateBulletsRequest):
    """**Gera bullets de destaque para o anúncio.** Requer IA configurada."""
    from api.src.functions.generator import generate_bullets
    if not get_settings().check_ai_configured():
        raise HTTPException(status_code=400, detail="IA não configurada.")
    bullets = await generate_bullets(
        keyword=req.keyword,
        marketplace=req.marketplace,
        attributes=req.attributes,
        n_bullets=req.n_bullets,
    )
    return {"bullets": bullets}


@app.post("/generate/description", tags=["Geração"])
async def generate_description_endpoint(req: GenerateDescriptionRequest):
    """**Gera descrição completa otimizada.** Requer IA configurada."""
    from api.src.functions.generator import generate_description
    if not get_settings().check_ai_configured():
        raise HTTPException(status_code=400, detail="IA não configurada.")
    desc = await generate_description(
        keyword=req.keyword,
        marketplace=req.marketplace,
        attributes=req.attributes,
        top_terms=req.top_terms,
    )
    return {"description": desc}