from api.src.pipeline.pipeline import Deduplicator
from api.src.types.listing import ListingNormalized, Marketplace, Seller


def _mk(listing_id: str, title: str) -> ListingNormalized:
    return ListingNormalized(
        marketplace=Marketplace.MERCADO_LIVRE,
        listing_id=listing_id,
        url=f"https://example.com/{listing_id}",
        title=title,
        price=1000.0,
        shipping_cost=0.0,
        final_price_estimate=1000.0,
        seller=Seller(seller_id="S1", nome="Loja A"),
    )


def test_dedup_similar_titles():
    listings = [
        _mk("A1", "Sofa Retratil 3 Lugares Cinza"),
        _mk("A2", "Sofa Retratil 3 Lugares Cinza"),
    ]
    unique = Deduplicator.run(listings)
    assert len(unique) == 1
