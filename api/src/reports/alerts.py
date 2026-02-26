from __future__ import annotations

from typing import Any


def generate_alerts_report(rules: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    return {"rules": rules, "events": events}
