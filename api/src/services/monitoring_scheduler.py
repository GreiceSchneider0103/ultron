from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from api.src.config import settings
from api.src.db import repository
from api.src.services.marketplace import get_connector

logger = logging.getLogger(__name__)

_state: dict[str, Any] = {
    "active": False,
    "last_run_at": None,
    "last_result": None,
    "last_error": None,
    "cycles": 0,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _platform_from_db(platform: str) -> str:
    value = (platform or "").strip().lower()
    if value == "meli":
        return "mercadolivre"
    return "magalu"


def _extract_baseline(normalized_data: dict[str, Any], raw_data: dict[str, Any]) -> dict[str, Any]:
    badges = normalized_data.get("badges") if isinstance(normalized_data.get("badges"), dict) else {}
    title = normalized_data.get("title") or raw_data.get("title") or ""
    price = normalized_data.get("final_price_estimate") or normalized_data.get("price") or raw_data.get("price")

    raw_variations = raw_data.get("variations", [])
    variation_tokens: list[str] = []
    if isinstance(raw_variations, list):
        for item in raw_variations:
            if isinstance(item, dict):
                token = str(item.get("id") or item.get("attribute_combinations") or item)
            else:
                token = str(item)
            variation_tokens.append(token)
    variation_tokens = sorted(dict.fromkeys(variation_tokens))

    shipping_flags = {
        "free_shipping": bool(badges.get("frete_gratis", False)),
        "full": bool(badges.get("full", False)),
        "shipping_cost": normalized_data.get("shipping_cost"),
    }

    return {
        "price": price,
        "title": title,
        "variations": variation_tokens,
        "badges": badges,
        "shipping_flags": shipping_flags,
    }


def _compute_changes(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = ["price", "title", "variations", "badges", "shipping_flags"]
    changes: dict[str, dict[str, Any]] = {}
    for field in fields:
        if previous.get(field) != current.get(field):
            changes[field] = {"before": previous.get(field), "after": current.get(field)}
    return changes


def _dedupe_signature(rule_id: str, listing_id: str, changes: dict[str, Any]) -> str:
    raw = json.dumps({"rule_id": rule_id, "listing_id": listing_id, "changes": changes}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fetch_active_rules(workspace_id: Optional[str], supabase_jwt: Optional[str]) -> list[dict[str, Any]]:
    if workspace_id:
        rows = repository.list_alert_rules(workspace_id=workspace_id, supabase_jwt=supabase_jwt)
        return [row for row in rows if row.get("is_active")]

    client = repository._make_client(supabase_jwt=None)
    if not client:
        return []
    try:
        resp = client.table("alert_rules").select("*").eq("is_active", True).execute()
        return resp.data or []
    except Exception as exc:
        logger.error("monitoring_fetch_rules_failed", error=str(exc))
        return []


def _fetch_workspace_listings(
    workspace_id: str,
    explicit_listing_ids: set[str],
    include_all_workspace: bool,
    supabase_jwt: Optional[str],
) -> list[dict[str, Any]]:
    client = repository._make_client(supabase_jwt=supabase_jwt)
    if not client:
        return []

    rows: list[dict[str, Any]] = []
    try:
        if explicit_listing_ids:
            for listing_id in explicit_listing_ids:
                resp = (
                    client.table("listings_current")
                    .select("*")
                    .eq("workspace_id", workspace_id)
                    .eq("id", listing_id)
                    .limit(1)
                    .execute()
                )
                if resp.data:
                    rows.append(resp.data[0])

        if include_all_workspace:
            resp = (
                client.table("listings_current")
                .select("*")
                .eq("workspace_id", workspace_id)
                .order("updated_at", desc=True)
                .limit(max(settings.MONITOR_MAX_LISTINGS_PER_CYCLE, 1))
                .execute()
            )
            rows.extend(resp.data or [])
    except Exception as exc:
        logger.error("monitoring_fetch_listings_failed", workspace_id=workspace_id, error=str(exc))
        return []

    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = row.get("id")
        if row_id:
            unique[row_id] = row
    return list(unique.values())


def _list_recent_events(rule_id: str, listing_id: str, since: datetime) -> list[dict[str, Any]]:
    client = repository._make_client(supabase_jwt=None)
    if not client:
        return []
    try:
        resp = (
            client.table("alert_events")
            .select("*")
            .eq("rule_id", rule_id)
            .eq("listing_id", listing_id)
            .gte("triggered_at", since.isoformat())
            .order("triggered_at", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("monitoring_fetch_recent_events_failed", error=str(exc))
        return []


def get_scheduler_health() -> dict[str, Any]:
    return {
        "scheduler_active": bool(_state.get("active")),
        "enabled_by_config": bool(settings.MONITOR_SCHEDULER_ENABLED),
        "environment": settings.ENVIRONMENT,
        "interval_minutes": settings.MONITOR_SCHEDULER_INTERVAL_MINUTES,
        "dedupe_hours": settings.MONITOR_ALERT_DEDUPE_HOURS,
        "last_run_at": _state.get("last_run_at"),
        "last_result": _state.get("last_result"),
        "last_error": _state.get("last_error"),
        "cycles": _state.get("cycles", 0),
    }


async def run_monitor_cycle(
    workspace_id: Optional[str] = None,
    supabase_jwt: Optional[str] = None,
    source: str = "scheduler",
) -> dict[str, Any]:
    started_at = _utcnow()
    created_events = 0
    checked_listings = 0
    processed_workspaces = 0

    rules = _fetch_active_rules(workspace_id=workspace_id, supabase_jwt=supabase_jwt)
    rules_by_workspace: dict[str, list[dict[str, Any]]] = {}
    for rule in rules:
        ws = rule.get("workspace_id")
        if ws:
            rules_by_workspace.setdefault(ws, []).append(rule)

    for ws_id, ws_rules in rules_by_workspace.items():
        processed_workspaces += 1
        explicit_listing_ids = {str(r["listing_id"]) for r in ws_rules if r.get("listing_id")}
        include_all_workspace = any(r.get("listing_id") is None for r in ws_rules)
        listings = _fetch_workspace_listings(
            workspace_id=ws_id,
            explicit_listing_ids=explicit_listing_ids,
            include_all_workspace=include_all_workspace,
            supabase_jwt=supabase_jwt if workspace_id else None,
        )

        for listing in listings:
            checked_listings += 1
            listing_uuid = listing.get("id")
            external_id = listing.get("external_id")
            platform = _platform_from_db(str(listing.get("platform") or ""))
            if not listing_uuid or not external_id:
                continue

            try:
                connector = get_connector(platform)
                raw = await connector.get_listing_details(str(external_id))
                normalized = await connector.normalize(raw)
                normalized_data = normalized.model_dump() if hasattr(normalized, "model_dump") else (normalized or {})

                previous_snapshot = repository.get_latest_snapshot(
                    workspace_id=ws_id,
                    listing_uuid=listing_uuid,
                    supabase_jwt=supabase_jwt if workspace_id else None,
                )
                repository.insert_snapshot_if_changed(
                    workspace_id=ws_id,
                    listing_uuid=listing_uuid,
                    raw_data=raw,
                    normalized_data=normalized_data,
                    derived_data={"source": source},
                    supabase_jwt=supabase_jwt if workspace_id else None,
                )

                if not previous_snapshot:
                    continue

                prev_base = _extract_baseline(
                    normalized_data=previous_snapshot.get("normalized_data") or {},
                    raw_data=previous_snapshot.get("raw_data") or {},
                )
                curr_base = _extract_baseline(normalized_data=normalized_data, raw_data=raw)
                changes = _compute_changes(prev_base, curr_base)
                if not changes:
                    continue

                dedupe_since = _utcnow() - timedelta(hours=max(settings.MONITOR_ALERT_DEDUPE_HOURS, 1))
                for rule in ws_rules:
                    rule_listing_id = rule.get("listing_id")
                    if rule_listing_id and str(rule_listing_id) != str(listing_uuid):
                        continue

                    signature = _dedupe_signature(str(rule["id"]), str(listing_uuid), changes)
                    recent_events = _list_recent_events(str(rule["id"]), str(listing_uuid), dedupe_since)
                    already_reported = any(
                        isinstance(evt.get("event_data"), dict)
                        and evt["event_data"].get("dedupe_signature") == signature
                        for evt in recent_events
                    )
                    if already_reported:
                        continue

                    event = repository.create_alert_event(
                        workspace_id=ws_id,
                        rule_id=str(rule["id"]),
                        listing_id=str(listing_uuid),
                        event_data={
                            "source": source,
                            "changes": changes,
                            "dedupe_signature": signature,
                            "baseline": {"previous": prev_base, "current": curr_base},
                        },
                        supabase_jwt=supabase_jwt if workspace_id else None,
                    )
                    if event:
                        created_events += 1
            except Exception as exc:
                logger.error(
                    "monitoring_cycle_listing_failed",
                    workspace_id=ws_id,
                    listing_id=str(listing_uuid),
                    error=str(exc),
                )

    result = {
        "source": source,
        "started_at": started_at.isoformat(),
        "finished_at": _utcnow().isoformat(),
        "processed_workspaces": processed_workspaces,
        "checked_listings": checked_listings,
        "created_events": created_events,
    }
    _state["last_run_at"] = result["finished_at"]
    _state["last_result"] = result
    _state["last_error"] = None
    _state["cycles"] = int(_state.get("cycles", 0)) + 1
    return result


async def scheduler_loop(stop_event: asyncio.Event) -> None:
    _state["active"] = True
    logger.info("monitor_scheduler_started", interval_minutes=settings.MONITOR_SCHEDULER_INTERVAL_MINUTES)
    try:
        while not stop_event.is_set():
            try:
                await run_monitor_cycle(source="scheduler")
            except Exception as exc:
                _state["last_error"] = str(exc)
                logger.error("monitor_scheduler_cycle_failed", error=str(exc))

            timeout = max(settings.MONITOR_SCHEDULER_INTERVAL_MINUTES, 1) * 60
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                continue
    finally:
        _state["active"] = False
        logger.info("monitor_scheduler_stopped")
