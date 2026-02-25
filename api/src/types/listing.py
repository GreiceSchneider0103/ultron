"""
Tipos de dados para normalização de anúncios
Segue o padrão ListingNormalized obrigatório
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Marketplace(str, Enum):
    """Marketplaces suportados"""
    MERCADO_LIVRE = "mercado_livre"
    MAGALU = "magalu"


class ShippingType(str, Enum):
    """Tipos de frete"""
    FRETE_GRATIS = "frete_gratis"
    FRETE_PAGO = "frete_pago"
    FULL = "full"


class ReputationLevel(str, Enum):
    """Níveis de reputação do vendedor"""
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    NEW = "new"


class ListingAttributes(BaseModel):
    """Atributos do produto (dimensões, material, etc)"""
    cor: Optional[str] = None
    material: Optional[str] = None
    largura: Optional[float] = None
    profundidade: Optional[float] = None
    altura: Optional[float] = None
    peso: Optional[float] = None
    densidade: Optional[str] = None
    
    # Campos específicos para móveis/estofados
    tipo_sofa: Optional[str] = None
    numero_lugares: Optional[int] = None
    tecido: Optional[str] = None
    formato: Optional[str] = None
    capacidade: Optional[int] = None


class MediaItem(BaseModel):
    """Item de mídia (imagem ou vídeo)"""
    url: str
    tipo: str = "foto"  # foto, video
    is_capa: bool = False
    tags: List[str] = Field(default_factory=list, description="Tags geradas por IA (Vision)")


class SellerMetrics(BaseModel):
    """Métricas do vendedor"""
    vendas_12m: Optional[int] = None
    reputacao: Optional[float] = None
    tempo_mercado_meses: Optional[int] = None
    perguntas_respondidas: Optional[int] = None
    delayed_rate: Optional[float] = None  # taxa de atraso


class Seller(BaseModel):
    """Informações do vendedor"""
    seller_id: str
    nome: str
    reputacao: ReputationLevel = ReputationLevel.NEW
    tempo_mercado_meses: Optional[int] = None
    metricas: Optional[SellerMetrics] = None
    tiene_tienda_oficial: Optional[bool] = None  # loja oficial
    tiene_CDI: Optional[bool] = None


class SocialProof(BaseModel):
    """Prova social (avaliações, perguntas)"""
    avaliacoes: int = 0
    nota_media: float = 0.0
    perguntas: int = 0
    respostas: int = 0


class Badges(BaseModel):
    """Selos do anúncio"""
    frete_gratis: bool = False
    full: bool = False
    premium: bool = False
    oficial: bool = False
    melhorei_preco: bool = False
    novo: bool = False
    melhores_opcoes: bool = False


class TextBlocks(BaseModel):
    """Blocos de texto do anúncio"""
    bullets: List[str] = Field(default_factory=list)
    descricao: Optional[str] = None


class ListingNormalized(BaseModel):
    """
    FORMATO OBRIGATÓRIO para todos os anúncios
    
    Este é o schema padrão que TODO anúncio deve seguir
    após passar pelo pipeline de normalização.
    """
    # Identificação
    marketplace: Marketplace
    listing_id: str
    url: str
    
    # Informações principais
    title: str
    price: float
    currency: str = "BRL"
    shipping_cost: float = 0.0
    final_price_estimate: float = Field(description="Preço final estimado (price + shipping)")
    
    # Categoria
    category_path: List[str] = Field(default_factory=list)
    category_id: Optional[str] = None
    
    # Atributos do produto
    attributes: ListingAttributes = Field(default_factory=ListingAttributes)
    
    # Mídia
    media: List[MediaItem] = Field(default_factory=list)
    
    # Vendedor
    seller: Seller
    
    # Prova social
    social_proof: SocialProof = Field(default_factory=SocialProof)
    
    # Selos
    badges: Badges = Field(default_factory=Badges)
    
    # Texto
    text_blocks: TextBlocks = Field(default_factory=TextBlocks)
    
    # SEO
    seo_terms: List[str] = Field(default_factory=list, description="Palavras-chave extraídas do título")
    
    # Análise IA (Novos campos para o Agente)
    ai_insights: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Insights gerados pelo LLM/Vision")
    
    # Metadados
    scraped_at: datetime = Field(default_factory=datetime.now)
    original_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Dados originais antes da normalização")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "marketplace": "mercado_livre",
                "listing_id": "MLB123456789",
                "title": "Sofá Retrátil 3 Lugares Veludo Cinza - Com Chaise",
                "price": 2599.90,
                "final_price_estimate": 2599.90,
                "attributes": {
                    "tipo_sofa": "retrátil",
                    "numero_lugares": 3,
                    "tecido": "veludo",
                    "cor": "cinza",
                    "largura": 220,
                    "profundidade": 85,
                    "altura": 95
                }
            }
        }
    }
