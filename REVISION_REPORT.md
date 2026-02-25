# 📋 RELATÓRIO DE REVISÃO DE CÓDIGO - ULTRON SYSTEM

**Data da Revisão:** 23/02/2026  
**Analista:** Engenheiro de Software Sênior + Arquiteto de Dados + Especialista em Marketplaces

---

## ✅ O QUE ESTÁ CORRETO

### 1. Infraestrutura Base (Boas Práticas)
- **Stack tecnológico adequado:** Python (FastAPI) + Next.js + Supabase
- **Autenticação implementada:** Sistema de login/register com Supabase Auth
- **Middleware de proteção:** Proxy configurado para proteger rotas autenticadas
- **Separação client/server:** Utils de Supabase corretamente separadas

### 2. Dependencies Python (requirements.txt)
- FastAPI + Uvicorn para API
- Celery + Redis para tarefas assíncronas
- Pydantic para validação de dados
- Supabase client para banco
- Tenacity para retry logic

### 3. Frontend Structure
- Next.js 16 com App Router
- TypeScript ativado
- TailwindCSS configurado
- Server Components para melhor performance

---

## ⚠️ PROBLEMAS ENCONTRADOS

### CRÍTICOS (Bloqueiam o MVP)

| # | Problema | Impacto | Local |
|---|----------|---------|-------|
| 1 | **API Python não existe** | Sistema não funciona | `api/` (vazio) |
| 2 | **Nenhum connector de marketplace** | Impossível coletar dados ML/Magalu | - |
| 3 | **Sem schema de banco de dados** | Sem persistência de dados | Supabase |
| 4 | **Nenhum tipo ListingNormalized** | Não segue padrão de dados obrigatório | - |
| 5 | **Sem funções de scraping/API** | Sem dados para analisar | - |

### GRAVES (Impactam Arquitetura)

| # | Problema | Impacto | Local |
|---|----------|---------|-------|
| 6 | **Arquitetura de camadas não existe** | Código misturado | - |
| 7 | **Sem Orquestrador** | Não há lógica de coordenação | - |
| 8 | **Sem Pipeline de dados** | Sem normalização/enriquecimento | - |
| 9 | **Sem Motor de avaliação** | Sem scoring SEO/conversão | - |
| 10 | **Sem Function Calling** | API não expõe ferramentas | - |

### MÉDIOS (Técnicos)

| # | Problema | Impacto | Local |
|---|----------|---------|-------|
| 11 | requirements.txt com encoding estranho | Leitura difícil | `api/requirements.txt` |
| 12 | Variáveis de ambiente não documentadas | Dificulta setup | - |
| 13 | Sem testes unitários | Baixa confiabilidade | - |
| 14 | Sem logs estruturados | Difícil debug | - |
| 15 | Frontend sem API client | Não consome dados | `web/` |

---

## 🛠️ MELHORIAS SUGERIDAS

### PRIORIDADE ALTA

#### 1. Criar estrutura de pastas da API
- **Motivo:** Arquitetura de camadas é obrigatória
- **Impacto:** Organiza código, facilita manutenção
- **Dificuldade:** Baixa
- **Arquivo:** Novo diretório `api/src/`

#### 2. Definir Schema ListingNormalized
- **Motivo:** Padrão de dados obrigatório pelo requisito
- **Impacto:** Normalização de todos os anúncios
- **Dificuldade:** Média
- **Arquivo:** `api/src/types/listing.py`

#### 3. Implementar Conectores de Marketplace
- **Motivo:** Coleta de dados é base do sistema
- **Impacto:** Alimenta todo o pipeline
- **Dificuldade:** Alta
- **Arquivo:** `api/src/connectors/`

#### 4. Criar Orquestrador de Agentes
- **Motivo:** Coordena chamadas e consolida insights
- **Impacto:** Core do sistema
- **Dificuldade:** Alta
- **Arquivo:** `api/src/orchestrator/`

### PRIORIDADE MÉDIA

#### 5. Implementar Motor de Scoring
- **Motivo:** Gera métricas SEO, conversão, competitividade
- **Impacto:** Diferencial competitivo
- **Dificuldade:** Média
- **Arquivo:** `api/src/scoring/`

#### 6. Pipeline de Dados
- **Motivo:** Normaliza e enriquece dados
- **Impacto:** Qualidade das análises
- **Dificuldade:** Média
- **Arquivo:** `api/src/pipeline/`

#### 7. Integrar Frontend com API
- **Motivo:** Exibir dados coletados
- **Impacto:** Usabilidade
- **Dificuldade:** Média
- **Arquivo:** `web/app/api/`

---

## 💻 COMO IMPLEMENTAR

### 1. Estrutura de Pastas Sugerida

```
ultron/
├── api/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app
│   │   ├── config.py                   # Configurações
│   │   ├── types/                      # TypeScript/Python types
│   │   │   ├── __init__.py
│   │   │   ├── listing.py              # ListingNormalized
│   │   │   ├── marketplace.py          # Enums de marketplace
│   │   │   └── scoring.py              # Tipos de score
│   │   ├── connectors/                 # Conectores de dados
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Classe base
│   │   │   ├── mercado_livre.py        # Connector ML
│   │   │   ├── magalu.py               # Connector Magalu
│   │   │   └── google_trends.py       # Connector Trends
│   │   ├── orchestrator/              # Orquestrador
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # Agente principal
│   │   │   ├── tasks.py                # Tarefas Celery
│   │   │   └── prompts.py              # Prompts do agente
│   │   ├── pipeline/                   # Pipeline de dados
│   │   │   ├── __init__.py
│   │   │   ├── normalizer.py           # Normalização
│   │   │   ├── enricher.py             # Enriquecimento
│   │   │   ├── deduplicator.py        # Deduplicação
│   │   │   └── storage.py             # Armazenamento
│   │   ├── scoring/                    # Motor de avaliação
│   │   │   ├── __init__.py
│   │   │   ├── seo.py                 # Score SEO
│   │   │   ├── conversion.py           # Score conversão
│   │   │   ├── competitiveness.py     # Score competitividade
│   │   │   └── gap_detection.py       # Detecção de gaps
│   │   ├── functions/                  # Function Calling
│   │   │   ├── __init__.py
│   │   │   ├── search.py              # search_marketplace_listings
│   │   │   ├── details.py             # get_listing_details
│   │   │   ├── seller.py              # get_seller_profile
│   │   │   ├── tracking.py            # track_price_history
│   │   │   ├── keywords.py            # extract_keywords
│   │   │   ├── titles.py              # suggest_title_variants
│   │   │   ├── audit.py               # audit_listing
│   │   │   ├── compare.py             # compare_vs_competitors
│   │   │   ├── documents.py           # parse_document
│   │   │   └── images.py              # analyze_images
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logger.py              # Logging estruturado
│   │       ├── cache.py               # Cache de requisições
│   │       └── validators.py          # Validações
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── connectors/
│   │   ├── orchestrator/
│   │   └── scoring/
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
└── web/
    ├── app/
    │   ├── (auth)/
    │   │   ├── login/
    │   │   └── register/
    │   ├── (dashboard)/
    │   │   ├── layout.tsx
    │   │   ├── page.tsx
    │   │   ├── research/
    │   │   ├── seo/
    │   │   ├── competitors/
    │   │   └── settings/
    │   ├── api/
    │   │   └── supabase/
    │   ├── layout.tsx
    │   └── page.tsx
    ├── components/
    │   ├── ui/
    │   ├── forms/
    │   ├── charts/
    │   └── dashboard/
    ├── lib/
    │   ├── api.ts
    │   ├── utils.ts
    │   └── constants.ts
    ├── hooks/
    ├── types/
    └── styles/
```

### 2. Definir ListingNormalized (Tipos Obrigatórios)

```python
# api/src/types/listing.py

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class Marketplace(str, Enum):
    MERCADO_LIVRE = "mercado_livre"
    MAGALU = "magalu"


class ShippingType(str, Enum):
    FRETE_GRATIS = "frete_gratis"
    FRETE_PAGO = "frete_pago"
    FULL = "full"


class ListingAttributes(BaseModel):
    cor: Optional[str] = None
    material: Optional[str] = None
    largura: Optional[float] = None
    profundidade: Optional[float] = None
    altura: Optional[float] = None
    peso: Optional[float] = None
    densidade: Optional[str] = None
    # Campos extras para móveis
    tipo_sofa: Optional[str] = None  # retrátil, fixo, chaise
    numero_lugares: Optional[int] = None
    tecido: Optional[str] = None


class MediaItem(BaseModel):
    url: str
    tipo: str  # foto, video
    is_capa: bool = False


class SellerMetrics(BaseModel):
    vendas_12m: Optional[int] = None
    reputacao: Optional[float] = None
    tempo_mercado: Optional[int] = None  # meses
    perguntas_respondidas: Optional[int] = None


class Seller(BaseModel):
    seller_id: str
    nome: str
    reputacao: str  # gold, silver, bronze
    tempo_mercado_meses: Optional[int] = None
    metricas: Optional[SellerMetrics] = None


class SocialProof(BaseModel):
    avaliacoes: int = 0
    nota_media: float = 0.0
    perguntas: int = 0
    respostas: int = 0


class Badges(BaseModel):
    frete_gratis: bool = False
    full: bool = False
    premium: bool = False
    oficial: bool = False
    melhorei_preco: bool = False


class TextBlocks(BaseModel):
    bullets: List[str] = Field(default_factory=list)
    descricao: Optional[str] = None


class ListingNormalized(BaseModel):
    """Formato obrigatório para todos os anúncios"""
    marketplace: Marketplace
    listing_id: str
    title: str
    price: float
    shipping_cost: float = 0.0
    final_price_estimate: float
    
    category_path: List[str]
    attributes: ListingAttributes = Field(default_factory=ListingAttributes)
    
    media: List[MediaItem] = Field(default_factory=list)
    seller: Seller
    social_proof: SocialProof = Field(default_factory=SocialProof)
    badges: Badges = Field(default_factory=Badges)
    
    text_blocks: TextBlocks = Field(default_factory=TextBlocks)
    seo_terms: List[str] = Field(default_factory=list)
    
    # Metadados
    scraped_at: str
    url: str
```

### 3. Criar Connector Base

```python
# api/src/connectors/base.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from api.src.types.listing import ListingNormalized


class BaseConnector(ABC):
    """Classe base para todos os conectores de marketplace"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = ""
    
    @abstractmethod
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Buscar anúncios por keyword"""
        pass
    
    @abstractmethod
    async def get_details(self, listing_id: str) -> Dict[str, Any]:
        """Buscar detalhes de um anúncio"""
        pass
    
    @abstractmethod
    async def get_seller(self, seller_id: str) -> Dict[str, Any]:
        """Buscar perfil do vendedor"""
        pass
    
    @abstractmethod
    async def normalize_listing(self, raw_data: Dict) -> ListingNormalized:
        """Converter dados brutos para ListingNormalized"""
        pass
    
    def validate_title(self, title: str, max_length: int = 60) -> bool:
        """Validar título conforme regras do marketplace"""
        return len(title) <= max_length
```

### 4. Criar Orquestrador

```python
# api/src/orchestrator/agent.py

from typing import List, Dict, Any, Optional
from api.src.types.listing import ListingNormalized
from api.src.connectors.base import BaseConnector
from api.src.scoring.seo import SEOScorer
from api.src.scoring.conversion import ConversionScorer


class MarketAgent:
    """
    Orquestrador principal do sistema
    Coordena coleta, análise e geração de insights
    """
    
    def __init__(self, connectors: Dict[str, BaseConnector]):
        self.connectors = connectors
        self.seo_scorer = SEOScorer()
        self.conversion_scorer = ConversionScorer()
    
    async def research_market(
        self,
        keyword: str,
        marketplace: str = "mercado_livre"
    ) -> Dict[str, Any]:
        """
        1. Coleta top anúncios por keyword
        2. Normaliza dados
        3. Gera insights
        """
        connector = self.connectors.get(marketplace)
        if not connector:
            raise ValueError(f"Connector {marketplace} não encontrado")
        
        # 1. Buscar anúncios
        raw_listings = await connector.search(query=keyword, limit=50)
        
        # 2. Normalizar
        normalized = []
        for raw in raw_listings:
            try:
                listing = await connector.normalize_listing(raw)
                normalized.append(listing)
            except Exception as e:
                print(f"Erro ao normalizar: {e}")
        
        # 3. Análises
        seo_analysis = await self._analyze_seo(normalized)
        competitors = await self._analyze_competitors(normalized)
        gaps = await self._detect_gaps(normalized, keyword)
        
        return {
            "keyword": keyword,
            "marketplace": marketplace,
            "total_results": len(raw_listings),
            "listings": normalized,
            "seo_analysis": seo_analysis,
            "competitors": competitors,
            "gaps": gaps,
        }
    
    async def audit_my_listing(
        self,
        my_listing: ListingNormalized,
        keyword: str
    ) -> Dict[str, Any]:
        """Auditar meu anúncio vs top 10 concorrentes"""
        
        # Buscar concorrentes
        market_data = await self.research_market(keyword)
        top_10 = market_data["listings"][:10]
        
        # Scores
        seo_score = self.seo_scorer.score(my_listing, top_10)
        conversion_score = self.conversion_scorer.score(my_listing, top_10)
        
        # Recomendações
        recommendations = self._generate_recommendations(
            my_listing, top_10, seo_score, conversion_score
        )
        
        return {
            "my_listing": my_listing,
            "seo_score": seo_score,
            "conversion_score": conversion_score,
            "competitors": top_10,
            "recommendations": recommendations,
        }
    
    async def _analyze_seo(self, listings: List[ListingNormalized]) -> Dict:
        """Analisar termos SEO dos top anúncios"""
        all_terms = []
        for listing in listings:
            all_terms.extend(listing.seo_terms)
        
        # Contar frequência
        term_counts = {}
        for term in all_terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        
        return {
            "top_terms": sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:20],
            "avg_title_length": sum(len(l.title) for l in listings) / len(listings),
        }
    
    async def _analyze_competitors(self, listings: List[ListingNormalized]) -> Dict:
        """Analisar concorrentes"""
        return {
            "avg_price": sum(l.price for l in listings) / len(listings),
            "price_range": {
                "min": min(l.price for l in listings),
                "max": max(l.price for l in listings),
            },
            "frete_gratis_count": sum(1 for l in listings if l.badges.frete_gratis),
            "full_count": sum(1 for l in listings if l.badges.full),
        }
    
    async def _detect_gaps(
        self, 
        listings: List[ListingNormalized], 
        keyword: str
    ) -> List[Dict]:
        """Detectar gaps de mercado"""
        gaps = []
        
        # Exemplo: analisar preço
        prices = [l.price for l in listings]
        avg_price = sum(prices) / len(prices)
        
        # Gap: preço muito acima ou abaixo da média
        # Gap: atributos não explorados pelos concorrentes
        # Gap: tipos de produto não atendidos
        
        return gaps
    
    def _generate_recommendations(
        self,
        my_listing: ListingNormalized,
        competitors: List[ListingNormalized],
        seo_score: Dict,
        conversion_score: Dict
    ) -> List[Dict]:
        """Gerar recomendações de otimização"""
        recommendations = []
        
        if seo_score["score"] < 70:
            recommendations.append({
                "type": "seo",
                "priority": "high",
                "title": "Melhorar título SEO",
                "suggestion": seo_score["suggestions"]
            })
        
        if conversion_score["score"] < 70:
            recommendations.append({
                "type": "conversion",
                "priority": "high",
                "title": "Melhorar taxa de conversão",
                "suggestion": conversion_score["suggestions"]
            })
        
        return recommendations
```

### 5. Definir API de Function Calling

```python
# api/src/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

from api.src.orchestrator.agent import MarketAgent
from api.src.types.listing import ListingNormalized, Marketplace
from api.src.connectors.mercado_livre import MercadoLivreConnector

app = FastAPI(title="Ultron API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Inicializar agentes
ml_connector = MercadoLivreConnector(os.getenv("ML_API_KEY"))
agent = MarketAgent({"mercado_livre": ml_connector})


# === SCHEMAS ===

class SearchRequest(BaseModel):
    keyword: str
    marketplace: str = "mercado_livre"
    limit: int = 50


class AuditRequest(BaseModel):
    listing_id: str
    keyword: str


class TitleSuggestRequest(BaseModel):
    keyword: str
    attributes: dict


# === ENDPOINTS ===

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/search")
async def search_marketplace_listings(req: SearchRequest):
    """Buscar anúncios por keyword"""
    try:
        result = await agent.research_market(
            keyword=req.keyword,
            marketplace=req.marketplace
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit")
async def audit_listing(req: AuditRequest):
    """Auditar meu anúncio vs concorrentes"""
    # Implementar busca do anúncio do usuário
    pass


@app.post("/suggest-title")
async def suggest_title_variants(req: TitleSuggestRequest):
    """Sugerir títulos otimizados"""
    # Implementar lógica de sugestão
    pass


@app.post("/extract-keywords")
async def extract_keywords(listing_ids: List[str]):
    """Extrair keywords dos top anúncios"""
    pass


# === EXPORTAR OPENAPI PARA LLM ===
# O FastAPI gera OpenAPI automaticamente
# Use /docs para testar
```

---

## 🧱 ARQUITETURA

### Status Atual: ❌ NÃO CONFORME

O código atual **NÃO** segue a arquitetura esperada porque:

1. **Não existe código na API** - apenas requirements.txt
2. **Frontend não consome API** - apenas estrutura básica
3. **Sem camadas definidas** - tudo misturado

### Arquitetura Proposta: ✅ CONFORME

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                      │
│  Dashboard │ Pesquisa │ SEO │ Concorrentes │ Configurações │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API / Function Calling
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    API (FastAPI + Celery)                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ORQUESTRADOR (Agent)                    │   │
│  │   • Decide quais dados buscar                        │   │
│  │   • Coordena chamadas                                │   │
│  │   • Consolida insights                               │   │
│  └─────────────────────────────────────────────────────┘   │
│         │              │              │              │       │
│         ▼              ▼              ▼              ▼       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │CONECTORES│  │ PIPELINE │  │ SCORING  │  │FUNCTIONS │    │
│  │    │     │  │    │     │  │    │     │  │    │     │    │
│  │ ML │Magalu│  │Normali- │  │SEO │Conv │  │Search │Audit│    │
│  │    │     │  │zação    │  │    │     │  │       │     │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│         │              │              │              │       │
│         ▼              ▼              ▼              ▼       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              ARMAZENAMENTO (BigQuery + Files)         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Escalabilidade: ✅ PRONTO

- **API:** FastAPI com Celery para tarefas assíncronas
- **Cache:** Redis integrado (já nas deps)
- **Banco:** Supabase (PostgreSQL) + BigQuery para analytics
- **Volume:** Arquitetura permite horizontal scaling

### Modularidade: ✅ PRONTO

- Conectores isolados
- Pipeline independentes
- Scoring como módulo separado
- Function calling como API REST

---

## 🚀 PRÓXIMOS PASSOS

### PRIORIDADE 1 (Semana 1-2) - MVP BASE

| # | Tarefa | Arquivo | Responsável |
|---|--------|---------|-------------|
| 1 | Criar estrutura de pastas | `api/src/*` | Dev |
| 2 | Definir tipos ListingNormalized | `api/src/types/listing.py` | Dev |
| 3 | Implementar connector base | `api/src/connectors/base.py` | Dev |
| 4 | Criar FastAPI básico | `api/src/main.py` | Dev |
| 5 | Setup .env e configurações | `api/.env.example` | Dev |

### PRIORIDADE 2 (Semana 3-4) - COLETAS

| # | Tarefa | Arquivo | Responsável |
|---|--------|---------|-------------|
| 6 | Implementar connector ML | `api/src/connectors/mercado_livre.py` | Dev |
| 7 | Implementar connector Magalu | `api/src/connectors/magalu.py` | Dev |
| 8 | Pipeline de normalização | `api/src/pipeline/normalizer.py` | Dev |
| 9 | API de busca (search) | `api/src/functions/search.py` | Dev |

### PRIORIDADE 3 (Semana 5-6) - ANÁLISES

| # | Tarefa | Arquivo | Responsável |
|---|--------|---------|-------------|
| 10 | Motor de scoring SEO | `api/src/scoring/seo.py` | Dev |
| 11 | Motor de scoring conversão | `api/src/scoring/conversion.py` | Dev |
| 12 | Orquestrador | `api/src/orchestrator/agent.py` | Dev |
| 13 | API de auditoria | `api/src/functions/audit.py` | Dev |

### PRIORIDADE 4 (Semana 7-8) - FRONTEND

| # | Tarefa | Arquivo | Responsável |
|---|--------|---------|-------------|
| 14 | Integrar API no frontend | `web/lib/api.ts` | Dev |
| 15 | Página de pesquisa | `web/app/(dashboard)/research/` | Dev |
| 16 | Página de SEO | `web/app/(dashboard)/seo/` | Dev |
| 17 | Página de concorrentes | `web/app/(dashboard)/competitors/` | Dev |

---

## 📌 CONCLUSÃO

O projeto está em **fase inicial** com apenas:
- ✅ Infraestrutura básica (FastAPI + Next.js + Supabase)
- ✅ Sistema de autenticação funcional
- ❌ Nenhuma lógica de negócio implementada

**Para atingir o MVP**, é necessário implementar:
1. **Conectores de marketplace** (ML + Magalu)
2. **Normalização de dados** (ListingNormalized)
3. **Orquestrador de agentes**
4. **Motor de scoring**
5. **Integração frontend**

A arquitetura proposta é **escalável, modular** e **pronta para function calling** e **BigQuery** conforme solicitado.

---

*Este documento deve ser atualizado conforme a implementação avançar.*
