"""
Ultron API - FastAPI Application
Sistema de inteligência para marketplaces
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.src.types.listing import ListingNormalized, Marketplace
from api.src.connectors.mercado_livre import MercadoLivreConnector
from api.src.connectors.magalu import MagaluConnector

try:
    from api.src.orchestrator.agent import MarketAgent
except ImportError:
    logger.warning("MarketAgent not found. Running in limited mode.")
    MarketAgent = None

from api.src.config import settings
from api.src.db import repository


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Estado global (em produção, usar dependency injection)
app_state = {
    "agent": None,
    "connectors": {}
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializar conectores ao iniciar"""
    
    logger.info("🚀 Inicializando Ultron API...")
    
    # Inicializar conectores
    ml_token = settings.ML_ACCESS_TOKEN
    
    connectors = {}
    
    if ml_token:
        connectors["mercado_livre"] = MercadoLivreConnector(ml_token)
        logger.info("✅ Mercado Livre connector inicializado")
    else:
        logger.warning("⚠️ ML_ACCESS_TOKEN não definido")
        
    # Inicializar Magalu (Sandbox)
    connectors["magalu"] = MagaluConnector()
    logger.info("✅ Magalu connector inicializado (Sandbox Mode)")
    
    # Criar agente
    if MarketAgent:
        agent = MarketAgent(connectors)
    else:
        agent = None
    
    app_state["agent"] = agent
    app_state["connectors"] = connectors
    
    logger.info("✅ Ultron API inicializada com sucesso")
    
    yield
    
    # Cleanup
    logger.info("🛑 Encerrando Ultron API...")


app = FastAPI(
    title="Ultron API",
    description="Sistema de inteligência para marketplaces (Mercado Livre, Magalu)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === MODELS ===

class SearchRequest(BaseModel):
    """Request para busca de anúncios"""
    keyword: str = Field(..., description="Keyword para busca")
    marketplace: str = Field("mercado_livre", description="Marketplace alvo")
    limit: int = Field(50, ge=1, le=100, description="Limite de resultados")
    price_min: Optional[float] = Field(None, description="Preço mínimo")
    price_max: Optional[float] = Field(None, description="Preço máximo")
    condition: Optional[str] = Field(None, description="Condição (new/used)")


class AuditRequest(BaseModel):
    """Request para auditoria de anúncio"""
    listing: ListingNormalized
    keyword: str


class TitleSuggestRequest(BaseModel):
    """Request para sugestão de título"""
    keyword: str
    attributes: dict
    marketplace: str = "mercado_livre"


class ValidateTitleRequest(BaseModel):
    """Request para validar título"""
    title: str
    marketplace: str = "mercado_livre"

class SyncRequest(BaseModel):
    """Request para sincronização operacional"""
    workspace_id: str = Field(default=settings.DEFAULT_WORKSPACE_ID)
    skus: List[str]
    limit: int = 50
    offset: int = 0

# === ENDPOINTS ===

@app.get("/")
async def root():
    """Raiz da API"""
    return {
        "name": "Ultron API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "connectors": list(app_state["connectors"].keys())
    }


@app.post("/search")
async def search_marketplace_listings(req: SearchRequest):
    """
    📊 Buscar anúncios por keyword
    
    Executa:
    1. Busca na API do marketplace
    2. Normaliza dados para ListingNormalized
    3. Gera análises (SEO, concorrentes, gaps)
    """
    
    agent = app_state.get("agent")
    if not agent:
        raise HTTPException(status_code=503, detail="Agent não inicializado")
    
    try:
        result = await agent.research_market(
            keyword=req.keyword,
            marketplace=req.marketplace,
            limit=req.limit
        )
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.post("/operations/sync")
async def sync_operations(req: SyncRequest):
    """
    🔄 Sincronizar dados operacionais (Seller Data)
    Focado em Magalu: Puxa portfólio, scores e estoque.
    """
    connector = app_state["connectors"].get("magalu")
    if not connector:
        raise HTTPException(status_code=503, detail="Magalu connector not initialized")
    
    results = {
        "synced": 0,
        "failed": 0,
        "errors": []
    }
    
    # Busca scores em lote (mais eficiente)
    scores_map = {}
    try:
        scores_list = await connector.get_scores(limit=req.limit, offset=req.offset)
        # Cria mapa SKU -> Score Data
        for item in scores_list:
            s_sku = item.get("sku", item.get("id"))
            if s_sku: scores_map[s_sku] = item
    except Exception as e:
        logger.error(f"Failed to fetch batch scores: {e}")

    for sku in req.skus:
        try:
            # 1. Busca Preço (Endpoint Real)
            price_data = await connector.get_price(sku)
            
            # 2. Combina com Score (se houver)
            raw_combined = {
                "sku": sku,
                "price_data": price_data,
                "score_data": scores_map.get(sku, {})
            }
            
            # 3. Normaliza
            normalized = await connector.normalize_listing(raw_combined)
            
            # 4. Salva no Supabase
            listing_uuid = repository.upsert_listings_current(
                workspace_id=req.workspace_id,
                platform="magalu",
                external_id=sku,
                raw_data=raw_combined,
                normalized_data=normalized.dict(),
                derived_data={"sync_source": "operations_sync"}
            )
            
            if listing_uuid:
                repository.insert_snapshot_if_changed(
                    workspace_id=req.workspace_id,
                    listing_uuid=listing_uuid,
                    raw_data=raw_combined,
                    normalized_data=normalized.dict(),
                    derived_data={"sync_source": "operations_sync"}
                )
                results["synced"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"Failed to upsert SKU {sku}")
                
        except Exception as e:
            logger.error(f"Error syncing SKU {sku}: {e}")
            results["failed"] += 1
            results["errors"].append(str(e))
            
    return results


@app.post("/audit")
async def audit_listing(req: AuditRequest):
    """
    🔍 Auditar meu anúncio vs concorrentes
    
    Compara seu anúncio com os top 20 concorrentes e gera:
    - Score SEO
    - Score de conversão
    - Score de competitividade
    - Recomendações de otimização
    """
    
    agent = app_state.get("agent")
    if not agent:
        raise HTTPException(status_code=503, detail="Agent não inicializado")
    
    try:
        result = await agent.audit_my_listing(
            my_listing=req.listing,
            keyword=req.keyword
        )
        return result
        
    except Exception as e:
        logger.error(f"Erro na auditoria: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/suggest-title")
async def suggest_title_variants(req: TitleSuggestRequest):
    """
    ✏️ Sugerir títulos otimizados
    
    Gera variações de título baseadas em:
    - Keyword da busca
    - Atributos do produto
    - Melhores práticas do marketplace
    """
    
    agent = app_state.get("agent")
    if not agent:
        raise HTTPException(status_code=503, detail="Agent não inicializado")
    
    try:
        suggestions = await agent.suggest_title(
            keyword=req.keyword,
            attributes=req.attributes,
            marketplace=req.marketplace
        )
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Erro ao sugerir títulos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate-title")
async def validate_title(req: ValidateTitleRequest):
    """
    ✅ Validar título
    
    Verifica se o título está dentro das regras do marketplace:
    - Comprimento máximo
    - Palavras proibidas
    """
    
    connector = app_state["connectors"].get(req.marketplace)
    if not connector:
        raise HTTPException(status_code=400, detail=f"Marketplace {req.marketplace} não suportado")
    
    validation = connector.validate_title(req.title)
    return validation


@app.get("/marketplaces")
async def list_marketplaces():
    """Listar marketplaces disponíveis"""
    return {
        "marketplaces": list(app_state["connectors"].keys())
    }


# === DOCUMENTAÇÃO ===
# Acesse /docs para Swagger UI
# Acesse /redoc para documentação alternativa
