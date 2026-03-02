"""
API Authentication — API Key 認証ミドルウェア
===============================================
FastAPI Depends で使用。3 つの認証方式をサポート:

  1. Header: X-API-Key: xxx
  2. Query:  ?api_key=xxx
  3. Bearer: Authorization: Bearer xxx

機能:
  - API Key バリデーション (billing.db 参照)
  - プラン情報の付与
  - レート制限 (メモリベース、分単位)
  - 認証失敗で 401/403/429
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

from .billing import BillingManager, Plan, PlanLimits, PLAN_LIMITS

_log = logging.getLogger("manaos.api_auth")

# API Key 取得元
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# レート制限: プランごとの 1 分あたりリクエスト数
_RATE_LIMITS: Dict[Plan, int] = {
    Plan.free: 5,         # 5 req/min
    Plan.pro: 30,         # 30 req/min
    Plan.enterprise: 120,  # 120 req/min
}


@dataclass
class AuthContext:
    """認証コンテキスト — 各リクエストに付与"""
    api_key: str
    plan: Plan
    limits: PlanLimits
    remaining_quota: int

    @property
    def priority(self) -> int:
        return self.limits.priority

    @property
    def can_auto_improve(self) -> bool:
        return self.limits.auto_improve


# ─── Rate Limiter ─────────────────────────────────────

class _RateLimiter:
    """インメモリ スライディングウィンドウ レートリミッター"""

    def __init__(self, window_seconds: int = 60):
        self._window = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)

    def check(self, api_key: str, limit: int) -> Tuple[bool, int]:
        """
        レート制限チェック。
        Returns: (allowed, remaining)
        """
        now = time.monotonic()
        cutoff = now - self._window

        # 古いエントリを削除
        self._requests[api_key] = [
            t for t in self._requests[api_key] if t > cutoff
        ]

        count = len(self._requests[api_key])
        remaining = max(0, limit - count)

        if count >= limit:
            return False, 0

        self._requests[api_key].append(now)
        return True, remaining - 1


_rate_limiter = _RateLimiter()

# シングルトン BillingManager (初回呼び出し時に作成)
_billing: Optional[BillingManager] = None


def _get_billing() -> BillingManager:
    global _billing
    if _billing is None:
        _billing = BillingManager()
    return _billing


# ─── FastAPI Dependencies ─────────────────────────────

async def get_api_key(
    header_key: Optional[str] = Security(_api_key_header),
    query_key: Optional[str] = Security(_api_key_query),
    request: Request = None,
) -> str:
    """
    リクエストから API Key を抽出。
    優先順位: Header > Query > Bearer
    """
    # 1) X-API-Key ヘッダー
    if header_key:
        return header_key

    # 2) ?api_key= クエリ
    if query_key:
        return query_key

    # 3) Authorization: Bearer xxx
    if request:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
            if token:
                return token

    # 認証なし → "default" キーを使用 (開発用)
    return "default"


async def require_auth(
    api_key: str = Depends(get_api_key),
) -> AuthContext:
    """
    API Key の完全認証 + レート制限。
    全エンドポイントで Depends(require_auth) として使用。
    """
    billing = _get_billing()

    # 1) API Key 有効性
    valid = await billing.validate_api_key(api_key)
    if not valid:
        _log.warning("Invalid API key: %s", api_key[:8])
        raise HTTPException(
            status_code=401,
            detail="Invalid or deactivated API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 2) プラン取得
    plan = await billing.get_plan(api_key)
    limits = PLAN_LIMITS[plan]

    # 3) レート制限
    rate_limit = _RATE_LIMITS.get(plan, 5)
    allowed, remaining = _rate_limiter.check(api_key, rate_limit)
    if not allowed:
        _log.warning("Rate limit exceeded: %s (plan=%s)", api_key[:8], plan.value)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({rate_limit} req/min for {plan.value} plan)",
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(rate_limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    # 4) 残りクォータ
    remaining_quota = await billing.get_remaining_quota(api_key)

    return AuthContext(
        api_key=api_key,
        plan=plan,
        limits=limits,
        remaining_quota=remaining_quota,
    )


async def optional_auth(
    api_key: str = Depends(get_api_key),
) -> Optional[AuthContext]:
    """
    ソフト認証 — 認証失敗でもエラーにならない。
    ヘルスチェックやダッシュボードなど公開エンドポイント用。
    """
    try:
        return await require_auth(api_key)
    except HTTPException:
        return None
