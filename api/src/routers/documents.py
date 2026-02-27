from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Optional

from PyPDF2 import PdfReader
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi import HTTPException

from api.src.auth import RequestContext, require_auth_context
from api.src.db import repository
from api.src.services.asset_storage import store_binary_asset
from api.src.services.multimodal import extract_structured_spec_from_text
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
    structured = extract_structured_spec_from_text(text)
    asset_meta = store_binary_asset(file_name=file.filename or "document.pdf", content=file_bytes, kind="documents")

    job_id = repository.create_job(
        workspace_id=ctx.workspace_id,
        job_type="document_upload",
        status="completed",
        result_summary={
            "filename": file.filename,
            "asset": asset_meta,
            "text": text,
            "pages": pages,
            "warning": warning,
            "structured_spec": structured.get("structured_spec", {}),
            "confidence": structured.get("confidence", {}),
        },
        supabase_jwt=ctx.token,
    )
    return {
        "workspace_id": ctx.workspace_id,
        "document_id": job_id,
        "status": "completed",
        "pages": pages,
        "warning": warning,
        "asset": asset_meta,
        "structured_spec": structured.get("structured_spec", {}),
        "confidence": structured.get("confidence", {}),
    }


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
    text = result.get("text", "")
    structured = result.get("structured_spec")
    confidence = result.get("confidence")
    if not structured:
        parsed = extract_structured_spec_from_text(text)
        structured = parsed.get("structured_spec", {})
        confidence = parsed.get("confidence", {})
    return {
        "document_id": document_id,
        "text": text,
        "pages": result.get("pages", 0),
        "warning": result.get("warning"),
        "asset": result.get("asset"),
        "structured_spec": structured,
        "confidence": confidence or {},
    }


@router.post("/analyze")
async def documents_analyze(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    text = str(req.get("text") or "").strip()
    document_id = req.get("document_id")
    if not text and document_id:
        job = repository.get_job(workspace_id=ctx.workspace_id, job_id=str(document_id), supabase_jwt=ctx.token)
        if not job:
            raise HTTPException(status_code=404, detail="Document not found.")
        text = str((job.get("result_summary") or {}).get("text") or "")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text or document_id for analysis.")
    parsed = extract_structured_spec_from_text(text)
    return {
        "workspace_id": ctx.workspace_id,
        "structured_spec": parsed.get("structured_spec", {}),
        "confidence": parsed.get("confidence", {}),
    }

