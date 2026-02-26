from api.src.db.mercado_livre import MercadoLivreRules


def test_forbidden_terms_ruleset_blocks_title():
    rules = MercadoLivreRules()
    result = rules.validate_title("Sofa Retratil com Frete Grátis Oferta")
    assert result["valid"] is False
    assert any("prohibited term" in issue.lower() for issue in result["issues"])
