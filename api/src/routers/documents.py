from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, UploadFile

from api.src.auth import RequestContext, require_auth_context
from api.src.db import repository
from api.src.routers.common import not_implemented

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def documents_upload(
    file: Optional[UploadFile] = File(default=None),
    ctx: RequestContext = Depends(require_auth_context),
):
    job_id = repository.create_job(
        workspace_id=ctx.workspace_id,
        job_type="document_upload",
        status="pending",
        result_summary={"filename": file.filename if file else None},
        supabase_jwt=ctx.token,
    )
    return {"workspace_id": ctx.workspace_id, "document_id": job_id, "status": "pending"}


@router.get("/{document_id}/extract")
async def documents_extract(
    document_id: str,
    extract_type: Optional[str] = None,
    ctx: RequestContext = Depends(require_auth_context),
):
    return not_implemented("documents", f"/api/documents/{document_id}/extract")


@router.post("/analyze")
async def documents_analyze(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    return not_implemented("documents", "/api/documents/analyze")
