"""Auth dependencies for Supabase Bearer JWT."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.src.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, Any] = {"expires_at": 0.0, "keys": []}


@dataclass
class RequestContext:
    user_id: str
    workspace_id: str
    token: str
    claims: Dict[str, Any]


async def _get_jwks() -> list[dict]:
    now = time.time()
    if _jwks_cache["expires_at"] > now and _jwks_cache["keys"]:
        return _jwks_cache["keys"]

    if not settings.SUPABASE_URL:
        return []

    jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
        _jwks_cache["keys"] = keys
        _jwks_cache["expires_at"] = now + 600
        return keys


async def _decode_supabase_jwt(token: str) -> Dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.") from exc

    keys = await _get_jwks()
    kid = header.get("kid")
    key_data = next((item for item in keys if item.get("kid") == kid), None)
    if not key_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token signing key not recognized.")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))
    issuer = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1" if settings.SUPABASE_URL else None

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[header.get("alg", "RS256")],
            issuer=issuer,
            options={"verify_aud": False},
        )
        return claims
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.") from exc


def _extract_workspace_id(claims: Dict[str, Any], x_workspace_id: Optional[str]) -> Optional[str]:
    if x_workspace_id:
        return x_workspace_id
    if claims.get("workspace_id"):
        return claims["workspace_id"]
    app_metadata = claims.get("app_metadata") or {}
    if app_metadata.get("workspace_id"):
        return app_metadata["workspace_id"]
    user_metadata = claims.get("user_metadata") or {}
    if user_metadata.get("workspace_id"):
        return user_metadata["workspace_id"]
    return None


async def require_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_workspace_id: Optional[str] = Header(default=None, alias="X-Workspace-Id"),
) -> RequestContext:
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    claims = await _decode_supabase_jwt(credentials.credentials)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.")

    workspace_id = _extract_workspace_id(claims=claims, x_workspace_id=x_workspace_id)
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace context missing. Provide X-Workspace-Id header or workspace_id claim.",
        )

    return RequestContext(
        user_id=user_id,
        workspace_id=workspace_id,
        token=credentials.credentials,
        claims=claims,
    )
