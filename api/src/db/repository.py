"""Supabase repository for Ultron schema V5."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional, List

from supabase import Client, create_client

from api.src.config import settings

logger = logging.getLogger(__name__)


def _platform_to_db(platform: str) -> str:
    value = (platform or "").strip().lower()
    if value in {"mercadolivre", "mercado_livre", "meli"}:
        return "meli"
    return "magalu"


def _make_client(supabase_jwt: Optional[str] = None) -> Optional[Client]:
    if not settings.SUPABASE_URL:
        return None

    # Prefer user-bound client (RLS) when JWT is available.
    if supabase_jwt and getattr(settings, "SUPABASE_ANON_KEY", None):
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        client.postgrest.auth(supabase_jwt)
        return client

    if settings.SUPABASE_SERVICE_ROLE_KEY:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    return None


def _content_hash(raw_data: Dict[str, Any], normalized_data: Dict[str, Any], derived_data: Dict[str, Any]) -> str:
    payload = {
        "raw_data": raw_data or {},
        "normalized_data": normalized_data or {},
        "derived_data": derived_data or {},
    }
    serialized = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def upsert_listing(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Legacy shim that delegates to V5 listings_current upsert."""
    listing_id = upsert_listings_current(
        workspace_id=kwargs.get("workspace_id", settings.DEFAULT_WORKSPACE_ID),
        platform=kwargs.get("platform", "mercado_livre"),
        external_id=kwargs.get("external_id", ""),
        raw_data=kwargs.get("raw_data", {}),
        normalized_data=kwargs.get("normalized_data", {}),
        derived_data=kwargs.get("derived_data", {}),
        supabase_jwt=kwargs.get("supabase_jwt"),
    )
    return {"ok": bool(listing_id), "id": listing_id}


def get_listing(
    workspace_id: str,
    platform: str,
    external_id: str,
    supabase_jwt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return None
    try:
        resp = (
            client.table("listings_current")
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("platform", _platform_to_db(platform))
            .eq("external_id", external_id)
            .limit(1)
            .execute()
        )
        return (resp.data or [None])[0]
    except Exception as exc:
        logger.error("repository_get_listing_failed: %s", exc)
        return None


def upsert_listings_current(
    workspace_id: str,
    platform: str,
    external_id: str,
    raw_data: Dict[str, Any],
    normalized_data: Dict[str, Any],
    derived_data: Dict[str, Any],
    supabase_jwt: Optional[str] = None,
) -> Optional[str]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        logger.warning("repository_client_unavailable")
        return None
    payload = {
        "workspace_id": workspace_id,
        "platform": _platform_to_db(platform),
        "external_id": external_id,
        "raw_data": raw_data or {},
        "normalized_data": normalized_data or {},
        "derived_data": derived_data or {},
    }
    try:
        resp = (
            client.table("listings_current")
            .upsert(payload, on_conflict="workspace_id,platform,external_id")
            .execute()
        )
        data = resp.data or []
        if not data:
            return None
        return data[0].get("id")
    except Exception as exc:
        logger.error("repository_upsert_listings_current_failed: %s", exc)
        return None


def insert_snapshot_if_changed(
    workspace_id: str,
    listing_uuid: str,
    raw_data: Dict[str, Any],
    normalized_data: Dict[str, Any],
    derived_data: Dict[str, Any],
    supabase_jwt: Optional[str] = None,
) -> bool:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return False
    content_hash = _content_hash(raw_data, normalized_data, derived_data)
    try:
        latest = (
            client.table("listing_snapshots")
            .select("content_hash")
            .eq("workspace_id", workspace_id)
            .eq("listing_id", listing_uuid)
            .order("captured_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_hash = (latest.data or [{}])[0].get("content_hash")
        if latest_hash == content_hash:
            return False

        client.table("listing_snapshots").insert(
            {
                "workspace_id": workspace_id,
                "listing_id": listing_uuid,
                "content_hash": content_hash,
                "raw_data": raw_data or {},
                "normalized_data": normalized_data or {},
                "derived_data": derived_data or {},
            }
        ).execute()
        return True
    except Exception as exc:
        logger.error("repository_insert_snapshot_failed: %s", exc)
        return False


def get_latest_snapshot(
    workspace_id: str,
    listing_uuid: str,
    supabase_jwt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return None
    try:
        resp = (
            client.table("listing_snapshots")
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("listing_id", listing_uuid)
            .order("captured_at", desc=True)
            .limit(1)
            .execute()
        )
        return (resp.data or [None])[0]
    except Exception as exc:
        logger.error("repository_get_latest_snapshot_failed: %s", exc)
        return None


def insert_audit(
    workspace_id: str,
    listing_id: str,
    scores: Dict[str, Any],
    penalties: Optional[List[Dict[str, Any]]] = None,
    recommendations: Optional[List[Any]] = None,
    idempotency_key: Optional[str] = None,
    supabase_jwt: Optional[str] = None,
) -> Optional[str]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return None
    payload = {
        "workspace_id": workspace_id,
        "listing_id": listing_id,
        "scores": scores or {},
        "penalties": penalties or [],
        "recommendations": recommendations or [],
    }
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    try:
        resp = client.table("audits").insert(payload).execute()
        data = resp.data or []
        return data[0].get("id") if data else None
    except Exception as exc:
        logger.error("repository_insert_audit_failed: %s", exc)
        return None


def create_job(
    workspace_id: str,
    job_type: str,
    idempotency_key: Optional[str] = None,
    status: str = "pending",
    result_summary: Optional[Dict[str, Any]] = None,
    supabase_jwt: Optional[str] = None,
) -> Optional[str]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return None
    payload = {
        "workspace_id": workspace_id,
        "type": job_type,
        "status": status,
        "result_summary": result_summary or {},
    }
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    try:
        resp = client.table("jobs").insert(payload).execute()
        data = resp.data or []
        return data[0].get("id") if data else None
    except Exception as exc:
        logger.error("repository_create_job_failed: %s", exc)
        return None


def update_job(
    workspace_id: str,
    job_id: str,
    status: str,
    result_summary: Optional[Dict[str, Any]] = None,
    supabase_jwt: Optional[str] = None,
) -> bool:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return False
    payload = {"status": status}
    if result_summary is not None:
        payload["result_summary"] = result_summary
    try:
        client.table("jobs").update(payload).eq("workspace_id", workspace_id).eq("id", job_id).execute()
        return True
    except Exception as exc:
        logger.error("repository_update_job_failed: %s", exc)
        return False


def get_job(workspace_id: str, job_id: str, supabase_jwt: Optional[str] = None) -> Optional[Dict[str, Any]]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return None
    try:
        resp = (
            client.table("jobs")
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        return (resp.data or [None])[0]
    except Exception as exc:
        logger.error("repository_get_job_failed: %s", exc)
        return None


def create_alert_rule(
    workspace_id: str,
    name: str,
    condition: Dict[str, Any],
    listing_id: Optional[str] = None,
    is_active: bool = True,
    supabase_jwt: Optional[str] = None,
) -> Optional[str]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return None
    payload = {
        "workspace_id": workspace_id,
        "listing_id": listing_id,
        "name": name,
        "condition": condition or {},
        "is_active": is_active,
    }
    try:
        resp = client.table("alert_rules").insert(payload).execute()
        data = resp.data or []
        return data[0].get("id") if data else None
    except Exception as exc:
        logger.error("repository_create_alert_rule_failed: %s", exc)
        return None


def list_alert_rules(workspace_id: str, supabase_jwt: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return []
    try:
        resp = client.table("alert_rules").select("*").eq("workspace_id", workspace_id).order("created_at", desc=True).execute()
        return resp.data or []
    except Exception as exc:
        logger.error("repository_list_alert_rules_failed: %s", exc)
        return []


def list_active_alert_rules_for_listing(
    workspace_id: str,
    listing_id: str,
    supabase_jwt: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return []
    try:
        resp = (
            client.table("alert_rules")
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("is_active", True)
            .or_(f"listing_id.eq.{listing_id},listing_id.is.null")
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("repository_list_active_alert_rules_for_listing_failed: %s", exc)
        return []


def update_alert_rule(
    workspace_id: str,
    alert_id: str,
    data: Dict[str, Any],
    supabase_jwt: Optional[str] = None,
) -> bool:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return False
    try:
        client.table("alert_rules").update(data).eq("workspace_id", workspace_id).eq("id", alert_id).execute()
        return True
    except Exception as exc:
        logger.error("repository_update_alert_rule_failed: %s", exc)
        return False


def delete_alert_rule(workspace_id: str, alert_id: str, supabase_jwt: Optional[str] = None) -> bool:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return False
    try:
        client.table("alert_rules").delete().eq("workspace_id", workspace_id).eq("id", alert_id).execute()
        return True
    except Exception as exc:
        logger.error("repository_delete_alert_rule_failed: %s", exc)
        return False


def list_alert_events(workspace_id: str, supabase_jwt: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return []
    try:
        resp = client.table("alert_events").select("*").eq("workspace_id", workspace_id).order("triggered_at", desc=True).execute()
        return resp.data or []
    except Exception as exc:
        logger.error("repository_list_alert_events_failed: %s", exc)
        return []


def create_alert_event(
    workspace_id: str,
    rule_id: str,
    listing_id: str,
    event_data: Dict[str, Any],
    status: str = "triggered",
    supabase_jwt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return None
    payload = {
        "rule_id": rule_id,
        "workspace_id": workspace_id,
        "listing_id": listing_id,
        "status": status,
        "event_data": event_data or {},
    }
    try:
        resp = client.table("alert_events").insert(payload).execute()
        data = resp.data or []
        return data[0] if data else None
    except Exception as exc:
        logger.error("repository_create_alert_event_failed: %s", exc)
        return None


def create_usage_log(
    workspace_id: str,
    feature: str,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tokens_used: int = 0,
    supabase_jwt: Optional[str] = None,
) -> Optional[str]:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return None
    payload_metadata = metadata.copy() if isinstance(metadata, dict) else {}
    if user_id:
        payload_metadata["user_id"] = user_id
    if trace_id:
        payload_metadata["trace_id"] = trace_id
    payload = {
        "workspace_id": workspace_id,
        "feature": feature,
        "tokens_used": int(tokens_used or 0),
        "metadata": payload_metadata,
    }
    try:
        resp = client.table("usage_logs").insert(payload).execute()
        data = resp.data or []
        return data[0].get("id") if data else None
    except Exception as exc:
        logger.error("repository_create_usage_log_failed: %s", exc)
        return None


def count_usage_logs(
    workspace_id: str,
    feature: str,
    supabase_jwt: Optional[str] = None,
) -> int:
    client = _make_client(supabase_jwt=supabase_jwt)
    if not client:
        return 0
    try:
        resp = (
            client.table("usage_logs")
            .select("id", count="exact", head=True)
            .eq("workspace_id", workspace_id)
            .eq("feature", feature)
            .execute()
        )
        return int(resp.count or 0)
    except Exception as exc:
        logger.error("repository_count_usage_logs_failed: %s", exc)
        return 0


def create_market_research_audit(summary: Any, listings: Any) -> Dict[str, Any]:
    """Compatibility helper used by old database.save_research_run callers."""
    return {
        "ok": True,
        "summary_present": summary is not None,
        "listings_count": len(listings or []),
    }
