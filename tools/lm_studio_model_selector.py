#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LM Studioのモデル選択を共通化し、テスト結果をキャッシュする。

- /v1/models から候補を取得
- 優先順位リストに沿って部分一致で選択
- 実推論（軽いchat/completions）で使用可能性を確認
- 結果をローカルJSONにキャッシュ（TTL）
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import List, Optional

import requests

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1").rstrip("/")


@dataclass(frozen=True)
class ModelSelectionConfig:
    preferred_models: List[str]
    skip_substrings: List[str]
    max_models: int = 3
    list_timeout_sec: int = 5
    test_timeout_sec: int = 10
    cache_ttl_sec: int = 15 * 60  # 15分
    cache_path: str = os.path.join(".cache", "lm_studio_model_cache.json")


def _ensure_cache_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _now() -> float:
    return time.time()


def _load_cache(path: str) -> Optional[dict]:
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(path: str, data: dict) -> None:
    try:
        _ensure_cache_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # キャッシュ失敗は致命ではない
        pass


def list_lm_studio_models(timeout_sec: int = 5) -> List[str]:
    r = requests.get(f"{LM_STUDIO_URL}/models", timeout=timeout_sec)
    r.raise_for_status()
    payload = r.json()
    if isinstance(payload, dict):
        data = payload.get("data", [])
        if isinstance(data, list):
            ids: List[str] = []
            for m in data:
                if isinstance(m, dict):
                    mid = m.get("id")
                    if isinstance(mid, str) and mid:
                        ids.append(mid)
            return ids
    return []


def _safe_lower(s: str) -> str:
    return s.strip().lower()


def _should_skip(model_id: str, skip_substrings: List[str]) -> bool:
    mid = _safe_lower(model_id)
    return any(_safe_lower(x) in mid for x in skip_substrings if x)


def test_model_chat(model_id: str, timeout_sec: int = 10) -> bool:
    """
    できるだけ軽い推論で「実際に使える」ことだけ確認する。
    """
    url = f"{LM_STUDIO_URL}/chat/completions"
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 3,
        "temperature": 0.0,
        "stream": False,
    }
    try:
        r = requests.post(url, json=data, timeout=timeout_sec)
        return r.status_code == 200
    except Exception:
        return False


def select_models(config: ModelSelectionConfig) -> List[str]:
    """
    優先順位に沿って最大config.max_modelsまで選び、実推論でテストする。
    キャッシュが有効ならキャッシュを返す（ただし /models の結果と突合）。
    """
    ttl = int(os.getenv("MANA_LMSTUDIO_MODEL_CACHE_TTL", str(config.cache_ttl_sec)))
    test_timeout = int(os.getenv("MANA_LMSTUDIO_TEST_TIMEOUT", str(config.test_timeout_sec)))

    cache = _load_cache(config.cache_path)
    if isinstance(cache, dict):
        ts = cache.get("timestamp")
        cached_models = cache.get("models")
        if isinstance(ts, (int, float)) and isinstance(cached_models, list):
            if _now() - float(ts) <= ttl:
                try:
                    available = set(list_lm_studio_models(timeout_sec=config.list_timeout_sec))
                    kept = [m for m in cached_models if isinstance(m, str) and m in available]
                    if kept:
                        return kept[: config.max_models]
                except Exception:
                    # サーバーが不安定でもキャッシュがあれば返す（空でなければ）
                    kept = [m for m in cached_models if isinstance(m, str)]
                    if kept:
                        return kept[: config.max_models]

    # キャッシュがない/期限切れ/突合で空 → 再選択
    available_models = list_lm_studio_models(timeout_sec=config.list_timeout_sec)
    selected: List[str] = []

    for preferred in config.preferred_models:
        pref_l = _safe_lower(preferred)
        for mid in available_models:
            if not isinstance(mid, str) or not mid:
                continue
            if _should_skip(mid, config.skip_substrings):
                continue
            mid_l = _safe_lower(mid)
            if pref_l in mid_l or mid_l in pref_l:
                if mid in selected:
                    break
                if test_model_chat(mid, timeout_sec=test_timeout):
                    selected.append(mid)
                break
        if len(selected) >= config.max_models:
            break

    # fallback: 先頭からテスト（保険）
    if not selected:
        for mid in available_models:
            if _should_skip(mid, config.skip_substrings):
                continue
            if test_model_chat(mid, timeout_sec=test_timeout):
                selected.append(mid)
                if len(selected) >= config.max_models:
                    break

    _save_cache(
        config.cache_path,
        {
            "timestamp": _now(),
            "models": selected,
            "available_count": len(available_models),
        },
    )
    return selected[: config.max_models]

