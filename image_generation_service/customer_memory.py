"""
Customer Memory — 顧客嗜好の記憶 (MRL Memory 連携)
=====================================================
MRL Memory (:5105) に顧客プロファイルを保存し、
リピート注文時に自動的にスタイル・パラメータを適用する。

保存される情報:
  - 好みのスタイル (よく使うプリセット)
  - カラーパレット傾向
  - 過去の高評価プロンプトパターン
  - 平均品質スコア推移
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

_log = logging.getLogger("manaos.customer_memory")

MRL_MEMORY_URL = os.getenv("MRL_MEMORY_URL", "http://127.0.0.1:5105")
_NAMESPACE = "image_gen_customer"
_client = httpx.AsyncClient(timeout=10)


class CustomerMemory:
    """顧客嗜好記憶マネージャ"""

    def __init__(self, memory_url: Optional[str] = None):
        self._url = memory_url or MRL_MEMORY_URL

    # ─── Profile CRUD ────────────────────────────────

    async def get_profile(self, customer_id: str) -> Dict[str, Any]:
        """顧客プロファイルを取得"""
        try:
            resp = await _client.get(
                f"{self._url}/api/memory/search",
                params={
                    "query": f"customer_profile:{customer_id}",
                    "namespace": _NAMESPACE,
                    "limit": 1,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    return json.loads(results[0].get("content", "{}"))
        except Exception as e:
            _log.warning("Failed to get profile for %s: %s", customer_id, e)
        return self._default_profile(customer_id)

    async def save_profile(self, customer_id: str, profile: Dict[str, Any]) -> bool:
        """顧客プロファイルを保存"""
        try:
            resp = await _client.post(
                f"{self._url}/api/memory/store",
                json={
                    "content": json.dumps(profile, ensure_ascii=False),
                    "metadata": {
                        "type": "customer_profile",
                        "customer_id": customer_id,
                        "namespace": _NAMESPACE,
                        "updated_at": datetime.now().isoformat(),
                    },
                },
            )
            return resp.status_code == 200
        except Exception as e:
            _log.warning("Failed to save profile for %s: %s", customer_id, e)
            return False

    # ─── Learning from Feedback ──────────────────────

    async def record_generation(
        self,
        customer_id: str,
        prompt: str,
        style: Optional[str],
        quality_score: Optional[float],
        rating: Optional[int] = None,
        params: Optional[Dict] = None,
    ):
        """生成結果を学習してプロファイルを更新"""
        profile = await self.get_profile(customer_id)

        # 生成回数
        profile["total_generations"] = profile.get("total_generations", 0) + 1

        # スタイル使用頻度
        if style:
            styles = profile.get("style_usage", {})
            styles[style] = styles.get(style, 0) + 1
            profile["style_usage"] = styles

        # 品質スコア推移
        if quality_score is not None:
            scores = profile.get("quality_scores", [])
            scores.append({"score": quality_score, "at": datetime.now().isoformat()})
            # 最新100件に限定
            profile["quality_scores"] = scores[-100:]
            # 平均更新
            recent = [s["score"] for s in profile["quality_scores"][-20:]]
            profile["avg_quality"] = round(sum(recent) / len(recent), 2)

        # 高評価プロンプト保存
        if rating and rating >= 4 and quality_score and quality_score >= 7:
            favorites = profile.get("favorite_prompts", [])
            favorites.append({
                "prompt": prompt[:200],
                "style": style,
                "score": quality_score,
                "rating": rating,
                "at": datetime.now().isoformat(),
            })
            profile["favorite_prompts"] = favorites[-50:]  # 最新50件

        # パラメータ傾向
        if params:
            pref = profile.get("param_preferences", {})
            for key in ["steps", "cfg_scale", "width", "height"]:
                if key in params:
                    values = pref.get(key, [])
                    values.append(params[key])
                    pref[key] = values[-20:]  # 最新20件
            profile["param_preferences"] = pref

        profile["last_active"] = datetime.now().isoformat()
        await self.save_profile(customer_id, profile)

    # ─── Smart Defaults ──────────────────────────────

    async def get_smart_defaults(self, customer_id: str) -> Dict[str, Any]:
        """
        過去の嗜好に基づくスマートデフォルトを返す。
        リクエスト作成時にこれをマージして使用。
        """
        profile = await self.get_profile(customer_id)
        defaults = {}

        # よく使うスタイル
        style_usage = profile.get("style_usage", {})
        if style_usage:
            favorite_style = max(style_usage, key=style_usage.get)
            if style_usage[favorite_style] >= 3:
                defaults["suggested_style"] = favorite_style

        # パラメータ平均
        pref = profile.get("param_preferences", {})
        for key in ["steps", "cfg_scale"]:
            values = pref.get(key, [])
            if len(values) >= 5:
                defaults[f"suggested_{key}"] = round(sum(values) / len(values), 1)

        # 推奨解像度
        widths = pref.get("width", [])
        heights = pref.get("height", [])
        if widths and heights:
            defaults["suggested_width"] = int(sum(widths) / len(widths))
            defaults["suggested_height"] = int(sum(heights) / len(heights))

        # 品質傾向
        defaults["avg_quality"] = profile.get("avg_quality")
        defaults["total_generations"] = profile.get("total_generations", 0)
        defaults["favorite_prompts_count"] = len(profile.get("favorite_prompts", []))

        return defaults

    async def get_favorite_prompts(
        self, customer_id: str, limit: int = 10
    ) -> List[Dict]:
        """高評価プロンプtr一覧"""
        profile = await self.get_profile(customer_id)
        favorites = profile.get("favorite_prompts", [])
        return sorted(favorites, key=lambda x: x.get("score", 0), reverse=True)[:limit]

    # ─── Analytics ───────────────────────────────────

    async def get_customer_analytics(self, customer_id: str) -> Dict[str, Any]:
        """顧客の分析データを返す"""
        profile = await self.get_profile(customer_id)

        style_usage = profile.get("style_usage", {})
        total = sum(style_usage.values()) if style_usage else 0

        quality_scores = profile.get("quality_scores", [])
        recent_scores = [s["score"] for s in quality_scores[-20:]]

        return {
            "customer_id": customer_id,
            "total_generations": profile.get("total_generations", 0),
            "avg_quality": profile.get("avg_quality"),
            "style_distribution": {
                k: {"count": v, "pct": round(v / total * 100, 1) if total else 0}
                for k, v in sorted(style_usage.items(), key=lambda x: x[1], reverse=True)
            },
            "quality_trend": {
                "recent_avg": round(sum(recent_scores) / len(recent_scores), 2) if recent_scores else None,
                "data_points": len(quality_scores),
            },
            "favorites_count": len(profile.get("favorite_prompts", [])),
            "last_active": profile.get("last_active"),
        }

    # ─── Internal ────────────────────────────────────

    @staticmethod
    def _default_profile(customer_id: str) -> Dict[str, Any]:
        return {
            "customer_id": customer_id,
            "total_generations": 0,
            "style_usage": {},
            "quality_scores": [],
            "favorite_prompts": [],
            "param_preferences": {},
            "avg_quality": None,
            "created_at": datetime.now().isoformat(),
            "last_active": None,
        }
