from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from core.config import _RPG_API_TOKEN


def _require_token(authorization: str | None = Header(None)) -> None:
    """Validate Bearer token for dangerous endpoints.
    If MANAOS_RPG_API_TOKEN is unset, auth is skipped (localhost-only use)."""
    if not _RPG_API_TOKEN:
        return  # token not configured – skip auth (dev/localhost)
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Bearer token required")
    if not hmac.compare_digest(token, _RPG_API_TOKEN):
        raise HTTPException(status_code=403, detail="invalid token")
