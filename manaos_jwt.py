#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JWT SSOT helpers.

- JWT secret: env var `JWT_SECRET_KEY` > `.jwt_secret` (persisted)
- HS256 signing key: if secret < 32 bytes, derive 32 bytes via SHA-256

This avoids PyJWT InsecureKeyLengthWarning while keeping compatibility when the
secret is already sufficiently long.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

from manaos_logger import get_logger

logger = get_logger(__name__)

JWT_ALGORITHM = "HS256"


def get_or_create_jwt_secret() -> str:
    """Return JWT secret key string. Persists when not configured."""
    key = os.getenv("JWT_SECRET_KEY", "").strip()
    if key:
        return key

    secret_file = Path(__file__).resolve().parent / ".jwt_secret"
    if secret_file.exists():
        return secret_file.read_text(encoding="utf-8").strip()

    key = secrets.token_urlsafe(32)
    secret_file.write_text(key, encoding="utf-8")
    try:
        # Best-effort. On Windows this may be a no-op.
        secret_file.chmod(0o600)
    except Exception:
        pass

    logger.warning("JWT_SECRET_KEY 未設定。.jwt_secret に自動生成しました")
    return key


def derive_hs256_signing_key(secret: str) -> bytes:
    """Derive HS256 key bytes.

    If the secret is at least 32 bytes, use it as-is to preserve compatibility.
    If shorter, derive 32 bytes via SHA-256 to avoid weak-key warnings.
    """
    raw = secret.encode("utf-8")
    if len(raw) >= 32:
        return raw
    return hashlib.sha256(raw).digest()


def accept_legacy_short_key() -> bool:
    """Whether to accept tokens signed with the raw short secret (legacy)."""
    return os.getenv("JWT_ACCEPT_LEGACY_SHORT_KEY", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }
