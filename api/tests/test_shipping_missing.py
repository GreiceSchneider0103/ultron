from api.src.types.listing import ListingNormalized, Marketplace, Seller


def test_shipping_missing_final_price_estimate_defaults_to_price():
    listing = ListingNormalized(
        marketplace=Marketplace.MERCADO_LIVRE,
        listing_id="MLB1",
        url="https://example.com",
        title="Sofa Retratil 3 Lugares",
        price=1200.0,
        shipping_cost=None,
        final_price_estimate=None,
        seller=Seller(seller_id="S1", nome="Loja A"),
    )
    assert listing.final_price_estimate == 1200.0
