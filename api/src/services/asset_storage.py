from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assets_root() -> Path:
    return Path.cwd() / "data" / "assets"


def store_binary_asset(file_name: str, content: bytes, kind: str = "documents") -> Dict[str, Any]:
    asset_id = str(uuid.uuid4())
    safe_name = file_name or f"{asset_id}.bin"
    target_dir = _assets_root() / kind
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{asset_id}_{safe_name}"
    target_file.write_bytes(content)
    created_at = _utc_now_iso()
    return {
        "asset_id": asset_id,
        "kind": kind,
        "filename": safe_name,
        "path": str(target_file),
        "link": str(target_file),
        "created_at": created_at,
        "updated_at": created_at,
    }


def register_link_asset(link: str, kind: str = "images", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    asset_id = str(uuid.uuid4())
    created_at = _utc_now_iso()
    payload = {
        "asset_id": asset_id,
        "kind": kind,
        "link": link,
        "created_at": created_at,
        "updated_at": created_at,
    }
    if metadata:
        payload["metadata"] = metadata
    return payload
