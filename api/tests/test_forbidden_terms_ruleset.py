from api.src.db.mercado_livre import MercadoLivreRules


def test_forbidden_terms_ruleset_blocks_title():
    rules = MercadoLivreRules()
    result = rules.validate_title("Sofa Retratil Oferta Limitada")
    assert result["valid"] is False
    assert len(result["issues"]) > 0
