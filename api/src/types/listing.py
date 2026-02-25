"""
Schema canônico para todos os anúncios coletados.
Todo conector DEVE produzir um objeto ListingNormalized.
"""
from __future__ import annotations
from typing import Optional, List
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ── Enumerações ───────────────────────────────────────────────

class Marketplace(str, Enum):
    MERCADO_LIVRE = "mercado_livre"
    MAGALU = "magalu"


class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"


class SellerReputation(str, Enum):
    PLATINUM = "platinum"
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    NEW = "new"
    UNKNOWN = "unknown"


# ── Sub-schemas ───────────────────────────────────────────────

class ListingAttributes(BaseModel):
    """Atributos físicos e técnicos do produto."""
    cor: Optional[str] = None
    material: Optional[str] = None
    largura_cm: Optional[float] = None
    profundidade_cm: Optional[float] = None
    altura_cm: Optional[float] = None
    peso_kg: Optional[float] = None
    densidade: Optional[str] = None          # ex: "33 kg/m³"
    tipo_produto: Optional[str] = None       # ex: "sofá retrátil"
    numero_lugares: Optional[int] = None
    tecido: Optional[str] = None
    extras: dict = Field(default_factory=dict)  # atributos livres do marketplace


class MediaItem(BaseModel):
    url: str
    tipo: MediaType = MediaType.PHOTO
    is_capa: bool = False
    has_text_overlay: Optional[bool] = None   # detectado por visão computacional
    quality_score: Optional[float] = None     # 0-100


class SellerMetrics(BaseModel):
    vendas_12m: Optional[int] = None
    cancelamentos_pct: Optional[float] = None
    reclamacoes_pct: Optional[float] = None
    atraso_entrega_pct: Optional[float] = None


class Seller(BaseModel):
    seller_id: str
    nome: str
    reputacao: SellerReputation = SellerReputation.UNKNOWN
    tempo_mercado_meses: Optional[int] = None
    metricas: Optional[SellerMetrics] = None
    is_official_store: bool = False


class SocialProof(BaseModel):
    avaliacoes_total: int = 0
    nota_media: float = 0.0
    perguntas_total: int = 0
    respostas_total: int = 0
    vendas_estimadas: Optional[int] = None   # quando disponível


class Badges(BaseModel):
    frete_gratis: bool = False
    full: bool = False            # ML FULL / entrega rápida
    premium: bool = False
    oficial: bool = False         # loja oficial
    melhorei_preco: bool = False
    anuncio_patrocinado: bool = False
    parcelamento_sem_juros: bool = False


class TextBlocks(BaseModel):
    bullets: List[str] = Field(default_factory=list)
    descricao: Optional[str] = None
    faq: List[dict] = Field(default_factory=list)   # [{pergunta, resposta}]


# ── Schema principal ──────────────────────────────────────────

class ListingNormalized(BaseModel):
    """
    Formato canônico único para anúncios de qualquer marketplace.
    Produzido por cada Connector e consumido por Pipeline, Scoring e Orquestrador.
    """
    # Identificação
    marketplace: Marketplace
    listing_id: str
    url: str

    # Preços
    price: float                          # preço atual
    price_original: Optional[float] = None  # preço sem desconto
    shipping_cost: float = 0.0
    final_price_estimate: float           # price + shipping_cost
    installments_max: Optional[int] = None
    installments_value: Optional[float] = None

    # Categorização
    category_path: List[str] = Field(default_factory=list)   # ["Móveis", "Sofás"]
    category_id: Optional[str] = None

    # Conteúdo
    title: str
    attributes: ListingAttributes = Field(default_factory=ListingAttributes)
    text_blocks: TextBlocks = Field(default_factory=TextBlocks)

    # Mídia
    media: List[MediaItem] = Field(default_factory=list)
    media_count: int = 0

    # Seller
    seller: Seller

    # Prova social
    social_proof: SocialProof = Field(default_factory=SocialProof)

    # Badges / diferenciais
    badges: Badges = Field(default_factory=Badges)

    # SEO
    seo_terms: List[str] = Field(default_factory=list)   # termos extraídos do título+desc

    # Metadados de coleta
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    position_in_search: Optional[int] = None   # posição no resultado de busca

    @field_validator("final_price_estimate", mode="before")
    @classmethod
    def set_final_price(cls, v, info):
        if v is None and info.data:
            return info.data.get("price", 0) + info.data.get("shipping_cost", 0)
        return v

    @field_validator("media_count", mode="before")
    @classmethod
    def set_media_count(cls, v, info):
        if v == 0 and info.data and info.data.get("media"):
            return len(info.data["media"])
        return v


# ── Schemas de scoring (saídas) ───────────────────────────────

class ScoreBreakdown(BaseModel):
    score: float          # 0-100
    label: str            # "Ruim" | "Regular" | "Bom" | "Excelente"
    details: dict = Field(default_factory=dict)
    suggestions: List[str] = Field(default_factory=list)


class ListingAuditResult(BaseModel):
    listing_id: str
    marketplace: Marketplace
    seo_score: ScoreBreakdown
    conversion_score: ScoreBreakdown
    competitiveness_score: ScoreBreakdown
    overall_score: float
    top_actions: List[str] = Field(default_factory=list)
    generated_titles: List[str] = Field(default_factory=list)
    generated_description: Optional[str] = None
    audit_at: datetime = Field(default_factory=datetime.utcnow)


class MarketResearchResult(BaseModel):
    keyword: str
    marketplace: Marketplace
    total_collected: int
    listings: List[ListingNormalized]
    price_range: dict         # {min, max, avg, median}
    top_seo_terms: List[dict] # [{term, freq}]
    competitor_summary: dict
    gaps: List[dict]
    research_at: datetime = Field(default_factory=datetime.utcnow)