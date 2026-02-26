from __future__ import annotations

from typing import Any, Optional

from api.src.db import repository


def _get_nested(data: dict, dotted_key: str) -> Any:
    value: Any = data
    for part in dotted_key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _pct_change(old: float, new: float) -> Optional[float]:
    if old == 0:
        return None
    return ((new - old) / old) * 100.0


def _is_triggered(condition: dict, current_data: dict, previous_data: dict) -> tuple[bool, dict]:
    field = condition.get("field")
    operator = condition.get("operator")
    threshold = float(condition.get("value", 0))

    current_val = _get_nested(current_data, field)
    previous_val = _get_nested(previous_data, field)

    if operator == "changed":
        triggered = current_val != previous_val
        return triggered, {"field": field, "previous": previous_val, "current": current_val}

    if operator in {"decreased_by_pct", "increased_by_pct"}:
        if current_val is None or previous_val is None:
            return False, {}
        try:
            current_num = float(current_val)
            previous_num = float(previous_val)
        except (TypeError, ValueError):
            return False, {}

        change = _pct_change(previous_num, current_num)
        if change is None:
            return False, {}

        if operator == "decreased_by_pct":
            triggered = change <= -abs(threshold)
        else:
            triggered = change >= abs(threshold)
        return triggered, {"field": field, "previous": previous_num, "current": current_num, "change_pct": round(change, 2)}

    return False, {}


async def check_and_fire_alerts(
    workspace_id: str,
    listing_uuid: str,
    current_data: dict,
    previous_data: dict,
    supabase_jwt: str,
) -> list[dict]:
    """
    Compara current_data vs previous_data.
    Para cada alert_rule ativa do workspace que referencia este listing,
    avalia a condição e registra um alert_event se disparada.

    Condições suportadas na v1:
    - { "field": "price", "operator": "decreased_by_pct", "value": 10 }
    - { "field": "price", "operator": "increased_by_pct", "value": 10 }
    - { "field": "badges.frete_gratis", "operator": "changed" }

    Retorna lista de alert_events criados.
    """
    rules = repository.list_active_alert_rules_for_listing(
        workspace_id=workspace_id,
        listing_id=listing_uuid,
        supabase_jwt=supabase_jwt,
    )
    created_events: list[dict] = []
    for rule in rules:
        condition = rule.get("condition", {}) or {}
        triggered, details = _is_triggered(condition, current_data=current_data, previous_data=previous_data)
        if not triggered:
            continue
        event = repository.create_alert_event(
            workspace_id=workspace_id,
            rule_id=rule["id"],
            listing_id=listing_uuid,
            event_data={"condition": condition, "details": details},
            supabase_jwt=supabase_jwt,
        )
        if event:
            created_events.append(event)
    return created_events
