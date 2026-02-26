from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Optional

from PyPDF2 import PdfReader
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi import HTTPException

from api.src.auth import RequestContext, require_auth_context
from api.src.db import repository
from api.src.routers.common import not_implemented
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def documents_upload(
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(require_auth_context),
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    pages = 0
    extracted_chunks: list[str] = []
    warning: Optional[str] = None
    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages = len(reader.pages)
        for page in reader.pages:
            extracted_chunks.append(page.extract_text() or "")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {exc}") from exc

    text = "\n".join([chunk for chunk in extracted_chunks if chunk]).strip()
    if not text:
        warning = "PDF sem texto extraivel"

    job_id = repository.create_job(
        workspace_id=ctx.workspace_id,
        job_type="document_upload",
        status="completed",
        result_summary={
            "filename": file.filename,
            "text": text,
            "pages": pages,
            "warning": warning,
        },
        supabase_jwt=ctx.token,
    )
    return {"workspace_id": ctx.workspace_id, "document_id": job_id, "status": "completed", "pages": pages, "warning": warning}


@router.get("/{document_id}/extract")
async def documents_extract(
    document_id: str,
    extract_type: Optional[str] = None,
    ctx: RequestContext = Depends(require_auth_context),
):
    job = repository.get_job(workspace_id=ctx.workspace_id, job_id=document_id, supabase_jwt=ctx.token)
    if not job:
        raise HTTPException(status_code=404, detail="Document not found.")
    result = job.get("result_summary") or {}
    return {
        "document_id": document_id,
        "text": result.get("text", ""),
        "pages": result.get("pages", 0),
        "warning": result.get("warning"),
    }


@router.post("/analyze")
async def documents_analyze(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    return not_implemented("documents", "/api/documents/analyze")

