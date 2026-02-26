"""Contract validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "contracts"


def load_contract(name: str) -> dict[str, Any]:
    path = CONTRACTS_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_against_contract(payload: Any, contract_name: str) -> tuple[bool, str | None]:
    try:
        import jsonschema
    except Exception:
        return True, "jsonschema_not_installed"

    try:
        schema = load_contract(contract_name)
        jsonschema.validate(instance=payload, schema=schema)
        return True, None
    except Exception as exc:
        return False, str(exc)
