import json
from pathlib import Path

import jsonschema

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"


def validate_against_contract(payload: dict, schema_filename: str) -> bool:
    """Valida payload contra schema JSON. Lança jsonschema.ValidationError se inválido."""
    schema_path = CONTRACTS_DIR / schema_filename
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)
    return True
