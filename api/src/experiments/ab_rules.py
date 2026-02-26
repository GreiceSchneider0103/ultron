from __future__ import annotations

from typing import Any


def enforce_single_change(hypothesis: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    target_metric = rules.get("target_metric", "ctr")
    window_days = int(rules.get("window_days", 7))
    change = hypothesis.get("change", {})
    change_keys = list(change.keys())
    single_change = {change_keys[0]: change[change_keys[0]]} if change_keys else {}
    return {
        "hypothesis": hypothesis.get("hypothesis", ""),
        "change": single_change,
        "window_days": window_days,
        "target_metric": target_metric,
        "valid": True,
    }
