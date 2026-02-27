from __future__ import annotations

from typing import Any, Optional

from fastapi.responses import JSONResponse


def error_payload(
    error_code: str,
    message: str,
    detail: Optional[Any] = None,
    trace_id: Optional[str] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"error_code": error_code, "message": message}
    if detail is not None:
        payload["detail"] = detail
    if trace_id:
        payload["trace_id"] = trace_id
    return payload


def error_response(
    status_code: int,
    error_code: str,
    message: str,
    detail: Optional[Any] = None,
    trace_id: Optional[str] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(error_code=error_code, message=message, detail=detail, trace_id=trace_id),
    )


def not_implemented(module: str, endpoint: str, message: str = "This endpoint is planned but not implemented yet.") -> JSONResponse:
    return error_response(
        status_code=501,
        error_code="not_implemented",
        message=message,
        detail={"module": module, "endpoint": endpoint},
    )
