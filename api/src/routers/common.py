from fastapi.responses import JSONResponse


def not_implemented(module: str, endpoint: str, message: str = "This endpoint is planned but not implemented yet.") -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_implemented",
            "module": module,
            "endpoint": endpoint,
            "message": message,
        },
    )
