"""
Billing — 課金 & 使用量管理 (SQLite バックエンド)
====================================================
プラン:
  Free:       ¥0     — 10枚/日, 512x512, Low priority
  Pro:        ¥2,980 — 100枚/日, 1024x1024, Medium priority
  Enterprise: ¥9,800 — 無制限, 2048x2048, High priority

機能:
  - API Key → プラン紐付け
  - 日次使用量カウンター（毎日 00:00 JST リセット）
  - 使用量超過で False → 429
  - 解像度制限チェック
  - GPU コスト推定
"""

from __future__ import annotations

import enum
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

_log = logging.getLogger("manaos.billing")

_DB_PATH = Path(os.getenv(
    "BILLING_DB_PATH",
    str(Path(__file__).resolve().parent.parent / "billing.db"),
))


class Plan(str, enum.Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


@dataclass
class PlanLimits:
    daily_quota: int          # 日次生成上限
    max_resolution: int       # 最大解像度 (片辺)
    priority: int             # 優先度 (1=low, 3=high)
    auto_improve: bool        # 自動改善ループ使用可否
    batch_max: int            # 最大バッチサイズ
    price_yen_monthly: int    # 月額 (円)


PLAN_LIMITS = {
    Plan.free: PlanLimits(
        daily_quota=10, max_resolution=512, priority=1,
        auto_improve=False, batch_max=1, price_yen_monthly=0,
    ),
    Plan.pro: PlanLimits(
        daily_quota=100, max_resolution=1024, priority=2,
        auto_improve=True, batch_max=2, price_yen_monthly=2980,
    ),
    Plan.enterprise: PlanLimits(
        daily_quota=999999, max_resolution=2048, priority=3,
        auto_improve=True, batch_max=4, price_yen_monthly=9800,
    ),
}


# ─── Database ─────────────────────────────────────────

@contextmanager
def _get_db():
    conn = sqlite3.connect(str(_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init_db():
    """テーブル初期化（べき等）"""
    with _get_db() as conn:
        # API Key → プラン紐付け
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                api_key     TEXT PRIMARY KEY,
                plan        TEXT NOT NULL DEFAULT 'free',
                label       TEXT,
                created_at  TEXT NOT NULL,
                active      INTEGER NOT NULL DEFAULT 1
            )
        """)
        # 日次使用量
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_daily (
                api_key     TEXT NOT NULL,
                usage_date  TEXT NOT NULL,
                count       INTEGER NOT NULL DEFAULT 0,
                total_cost  REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (api_key, usage_date)
            )
        """)
        # 使用ログ (個別)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key     TEXT NOT NULL,
                job_id      TEXT,
                cost_yen    REAL NOT NULL,
                width       INTEGER,
                height      INTEGER,
                steps       INTEGER,
                created_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_log_key_date
            ON usage_log (api_key, created_at)
        """)

        # デフォルト API Key 作成 (まだなければ)
        existing = conn.execute(
            "SELECT 1 FROM api_keys WHERE api_key = 'default'"
        ).fetchone()
        if not existing:
            conn.execute(
                """INSERT INTO api_keys (api_key, plan, label, created_at)
                   VALUES ('default', 'enterprise', 'Default dev key', ?)""",
                (datetime.now().isoformat(),),
            )
            _log.info("Created default API key (enterprise plan)")

    _log.info("Billing DB initialized: %s", _DB_PATH)


class BillingManager:
    """課金チェック & 使用量管理 (SQLite バックエンド)"""

    def __init__(self):
        _init_db()
        _log.info("BillingManager initialized (db=%s)", _DB_PATH)

    # ─── API Key Management ───────────────────────────

    async def create_api_key(
        self, api_key: str, plan: Plan = Plan.free, label: str = "",
    ) -> bool:
        """新しい API Key を登録"""
        try:
            with _get_db() as conn:
                conn.execute(
                    """INSERT INTO api_keys (api_key, plan, label, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (api_key, plan.value, label, datetime.now().isoformat()),
                )
            _log.info("Created API key: %s (plan=%s)", api_key[:8] + "...", plan.value)
            return True
        except sqlite3.IntegrityError:
            _log.warning("API key already exists: %s", api_key[:8])
            return False

    async def deactivate_api_key(self, api_key: str) -> bool:
        """API Key を無効化"""
        with _get_db() as conn:
            updated = conn.execute(
                "UPDATE api_keys SET active = 0 WHERE api_key = ?",
                (api_key,),
            ).rowcount
        return updated > 0

    async def validate_api_key(self, api_key: str) -> bool:
        """API Key が有効か確認"""
        with _get_db() as conn:
            row = conn.execute(
                "SELECT active FROM api_keys WHERE api_key = ?",
                (api_key,),
            ).fetchone()
        return row is not None and row["active"] == 1

    # ─── Plan & Quota ─────────────────────────────────

    async def get_plan(self, api_key: str) -> Plan:
        """API Key からプランを取得"""
        with _get_db() as conn:
            row = conn.execute(
                "SELECT plan FROM api_keys WHERE api_key = ? AND active = 1",
                (api_key,),
            ).fetchone()
        if row is None:
            return Plan.free  # 未登録 = Free
        return Plan(row["plan"])

    async def get_plan_limits(self, api_key: str) -> PlanLimits:
        """API Key のプラン制限を取得"""
        plan = await self.get_plan(api_key)
        return PLAN_LIMITS[plan]

    async def check_quota(self, api_key: str) -> bool:
        """
        日次使用量上限チェック。超過時は False。
        """
        plan = await self.get_plan(api_key)
        limits = PLAN_LIMITS[plan]
        today = date.today().isoformat()

        with _get_db() as conn:
            row = conn.execute(
                """SELECT count FROM usage_daily
                   WHERE api_key = ? AND usage_date = ?""",
                (api_key, today),
            ).fetchone()

        used = row["count"] if row else 0
        remaining = limits.daily_quota - used

        if remaining <= 0:
            _log.warning(
                "Quota exceeded for %s (plan=%s, used=%d/%d)",
                api_key[:8], plan.value, used, limits.daily_quota,
            )
            return False

        _log.debug(
            "Quota OK: %s used=%d/%d remaining=%d",
            api_key[:8], used, limits.daily_quota, remaining,
        )
        return True

    async def check_resolution(
        self, api_key: str, width: int, height: int,
    ) -> bool:
        """解像度がプランの制限内か確認"""
        limits = await self.get_plan_limits(api_key)
        return max(width, height) <= limits.max_resolution

    async def get_remaining_quota(self, api_key: str) -> int:
        """残り生成可能枚数"""
        plan = await self.get_plan(api_key)
        limits = PLAN_LIMITS[plan]
        today = date.today().isoformat()

        with _get_db() as conn:
            row = conn.execute(
                """SELECT count FROM usage_daily
                   WHERE api_key = ? AND usage_date = ?""",
                (api_key, today),
            ).fetchone()

        used = row["count"] if row else 0
        return max(0, limits.daily_quota - used)

    # ─── Usage Recording ──────────────────────────────

    async def record_usage(
        self,
        api_key: str,
        cost_yen: float,
        job_id: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
    ):
        """使用量を記録（日次カウンター + 詳細ログ）"""
        today = date.today().isoformat()
        now = datetime.now().isoformat()

        with _get_db() as conn:
            # 日次カウンター (UPSERT)
            conn.execute(
                """INSERT INTO usage_daily (api_key, usage_date, count, total_cost)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(api_key, usage_date)
                   DO UPDATE SET count = count + 1,
                                 total_cost = total_cost + ?""",
                (api_key, today, cost_yen, cost_yen),
            )
            # 使用ログ
            conn.execute(
                """INSERT INTO usage_log
                   (api_key, job_id, cost_yen, width, height, steps, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (api_key, job_id, cost_yen, width, height, steps, now),
            )

        _log.debug("Recorded usage: %s job=%s cost=¥%.4f", api_key[:8], job_id[:8], cost_yen)

    # ─── Cost Estimation ──────────────────────────────

    async def estimate_cost(
        self,
        width: int,
        height: int,
        steps: int,
        batch_size: int = 1,
    ) -> float:
        """
        生成コスト推定 (円)
        RTX 5080 ~300W, 電気代 ~30円/kWh
        512x512 20steps ≈ 5秒 ≈ 0.4Wh ≈ 0.012円
        """
        pixels = width * height
        base_cost = (pixels / (512 * 512)) * (steps / 20) * 0.012
        return round(base_cost * batch_size, 4)

    # ─── Dashboard ────────────────────────────────────

    # 決済APIスタブ
    def create_stripe_payment(self, user_id: str, plan: str) -> dict:
        """
        Stripe決済スタブ（本番はStripe API連携）
        """
        # 実際はstripe.PaymentIntent.create()等
        return {
            "provider": "stripe",
            "plan": plan,
            "user_id": user_id,
            "payment_url": f"https://checkout.stripe.com/pay/test_{plan}_{user_id}",
            "status": "stub",
        }

    def create_komoju_payment(self, user_id: str, plan: str) -> dict:
        """
        KOMOJU決済スタブ（本番はKOMOJU API連携）
        """
        return {
            "provider": "komoju",
            "plan": plan,
            "user_id": user_id,
            "payment_url": f"https://checkout.komoju.com/pay/test_{plan}_{user_id}",
            "status": "stub",
        }

    async def get_billing_dashboard(self, api_key: str) -> Dict[str, Any]:
        """課金ダッシュボード"""
        plan = await self.get_plan(api_key)
        limits = PLAN_LIMITS[plan]
        remaining = await self.get_remaining_quota(api_key)
        today = date.today().isoformat()

        with _get_db() as conn:
            # 今日の使用量
            today_row = conn.execute(
                """SELECT count, total_cost FROM usage_daily
                   WHERE api_key = ? AND usage_date = ?""",
                (api_key, today),
            ).fetchone()

            # 過去 30 日の累計
            thirty_days = conn.execute(
                """SELECT SUM(count) as total, SUM(total_cost) as cost
                   FROM usage_daily WHERE api_key = ?
                   AND usage_date >= date(?, '-30 days')""",
                (api_key, today),
            ).fetchone()

            # 全 API Key 数
            key_count = conn.execute(
                "SELECT COUNT(*) FROM api_keys WHERE active = 1"
            ).fetchone()[0]

        return {
            "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
            "plan": plan.value,
            "limits": {
                "daily_quota": limits.daily_quota,
                "max_resolution": limits.max_resolution,
                "priority": limits.priority,
                "auto_improve": limits.auto_improve,
                "batch_max": limits.batch_max,
                "price_yen_monthly": limits.price_yen_monthly,
            },
            "today": {
                "used": today_row["count"] if today_row else 0,
                "remaining": remaining,
                "cost_yen": round(today_row["total_cost"], 4) if today_row else 0,
            },
            "month": {
                "total_generations": thirty_days["total"] or 0,
                "total_cost_yen": round(thirty_days["cost"] or 0, 4),
            },
            "active_keys": key_count,
        }
