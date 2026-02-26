"""Smoke tests: valida payloads canônicos contra os schemas JSON de contrato."""

from api.src.types.listing import (
    Badges,
    ListingAttributes,
    ListingNormalized,
    Marketplace,
    Seller,
    SellerReputation,
    SocialProof,
    TextBlocks,
)
from api.src.reports.market_dashboard import generate_market_dashboard
from api.src.reports.audit_report import generate_audit_report
from api.src.contracts.validator import validate_against_contract


def _make_listing() -> ListingNormalized:
    return ListingNormalized(
        marketplace=Marketplace.MERCADO_LIVRE,
        listing_id="MLB123",
        url="https://www.mercadolivre.com.br/p/MLB123",
        title="Sofa Retratil 3 Lugares Suede Cinza",
        price=1500.0,
        shipping_cost=0.0,
        final_price_estimate=1500.0,
        seller=Seller(seller_id="seller1", nome="Loja Teste", reputacao=SellerReputation.GOLD),
        social_proof=SocialProof(avaliacoes_total=10, nota_media=4.5),
        badges=Badges(frete_gratis=True),
        text_blocks=TextBlocks(bullets=["Suede de alta qualidade", "3 lugares"]),
        attributes=ListingAttributes(cor="Cinza", material="Suede"),
    )


def test_listing_normalized_contract():
    listing = _make_listing()
    payload = listing.to_contract_payload()
    assert validate_against_contract(payload, "listing_normalized.schema.json")


def test_report_outputs_contract():
    listing_payload = _make_listing().to_contract_payload()
    price_range = {"min": 1200.0, "max": 2000.0, "avg": 1600.0, "median": 1550.0}
    competitor_summary = {"total_analyzed": 10, "frete_gratis_pct": 60.0}

    dashboard = generate_market_dashboard([listing_payload], price_range, competitor_summary)
    audit = generate_audit_report(
        scores={"seo": 75, "conversion": 68},
        recommendations=["Adicionar mais fotos"],
        metadata={"version": 1},
    )

    report_payload = {"market_dashboard": dashboard, "audit_report": audit}
    assert validate_against_contract(report_payload, "report_outputs.schema.json")
