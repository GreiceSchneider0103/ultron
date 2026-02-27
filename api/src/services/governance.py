from __future__ import annotations

from typing import Any, Dict, Optional

from api.src.db import repository


def track_expensive_call(
    *,
    workspace_id: str,
    user_id: str,
    feature: str,
    trace_id: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
    supabase_jwt: Optional[str] = None,
) -> Optional[str]:
    return repository.create_usage_log(
        workspace_id=workspace_id,
        feature=feature,
        user_id=user_id,
        trace_id=trace_id,
        metadata=metadata or {},
        supabase_jwt=supabase_jwt,
    )
