#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 内発ToDo品質改善ループ
- Rejected理由を記録
- 次回生成に反映（禁止タグ/粒度/時間帯）
- 同じ却下が続くなら提案カテゴリを変える
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
import json
from collections import defaultdict, Counter

# 設定（環境変数から取得、デフォルト値あり）
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault"))
SYSTEM_DIR = VAULT_PATH / "ManaOS" / "System"
REJECTION_LOG = SYSTEM_DIR / "todo_rejections.jsonl"
QUALITY_CONFIG = SYSTEM_DIR / "todo_quality_config.json"

# デフォルト設定
DEFAULT_QUALITY_CONFIG = {
    "banned_tags": [],
    "banned_categories": [],
    "min_granularity": "medium",  # "low" | "medium" | "high"
    "banned_time_ranges": [],  # [{"start": "HH:MM", "end": "HH:MM"}]
    "rejection_threshold": 3,  # 同じ理由で3回却下されたらカテゴリ変更
    "category_alternatives": {
        "maintenance": ["optimization", "enhancement"],
        "optimization": ["maintenance", "monitoring"],
        "enhancement": ["optimization", "maintenance"],
    },
}


def load_quality_config() -> Dict[str, Any]:
    """品質設定を読み込み"""
    if QUALITY_CONFIG.exists():
        return json.loads(QUALITY_CONFIG.read_text(encoding="utf-8"))
    return DEFAULT_QUALITY_CONFIG.copy()


def save_quality_config(config: Dict[str, Any]) -> None:
    """品質設定を保存"""
    QUALITY_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def record_rejection(todo_id: str, reason: str, category: str, tags: List[str],
                    granularity: str, rejected_at: Optional[datetime] = None) -> None:
    """却下理由を記録"""
    rejection = {
        "todo_id": todo_id,
        "reason": reason,
        "category": category,
        "tags": tags,
        "granularity": granularity,
        "rejected_at": (rejected_at or datetime.now()).isoformat(),
    }

    REJECTION_LOG.parent.mkdir(parents=True, exist_ok=True)

    with open(REJECTION_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rejection, ensure_ascii=False) + '\n')


def load_rejections(days: int = 30) -> List[Dict[str, Any]]:
    """却下履歴を読み込み"""
    if not REJECTION_LOG.exists():
        return []

    cutoff_date = datetime.now() - timedelta(days=days)
    rejections = []

    with open(REJECTION_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                rejection = json.loads(line.strip())
                rejected_at = datetime.fromisoformat(rejection["rejected_at"])

                if rejected_at >= cutoff_date:
                    rejections.append(rejection)
            except Exception:
                continue

    return rejections


def analyze_rejection_patterns(rejections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """却下パターンを分析"""
    if not rejections:
        return {}

    # 理由別カウント
    reason_counts = Counter(r["reason"] for r in rejections)

    # カテゴリ別カウント
    category_counts = Counter(r["category"] for r in rejections)

    # タグ別カウント
    tag_counts = Counter()
    for r in rejections:
        for tag in r.get("tags", []):
            tag_counts[tag] += 1

    # 粒度別カウント
    granularity_counts = Counter(r.get("granularity", "unknown") for r in rejections)

    # 時間帯別カウント
    hour_counts = Counter()
    for r in rejections:
        rejected_at = datetime.fromisoformat(r["rejected_at"])
        hour_counts[rejected_at.hour] += 1

    return {
        "reason_counts": dict(reason_counts),
        "category_counts": dict(category_counts),
        "tag_counts": dict(tag_counts),
        "granularity_counts": dict(granularity_counts),
        "hour_counts": dict(hour_counts),
        "total_rejections": len(rejections),
    }


def update_quality_config_from_rejections() -> Dict[str, Any]:
    """却下履歴から品質設定を更新"""
    config = load_quality_config()
    rejections = load_rejections(days=30)

    if not rejections:
        return config

    patterns = analyze_rejection_patterns(rejections)

    # 禁止タグの更新（3回以上却下されたタグ）
    banned_tags = set(config.get("banned_tags", []))
    for tag, count in patterns.get("tag_counts", {}).items():
        if count >= config.get("rejection_threshold", 3):
            banned_tags.add(tag)
    config["banned_tags"] = list(banned_tags)

    # 禁止カテゴリの更新
    banned_categories = set(config.get("banned_categories", []))
    for category, count in patterns.get("category_counts", {}).items():
        if count >= config.get("rejection_threshold", 3):
            banned_categories.add(category)
    config["banned_categories"] = list(banned_categories)

    # 粒度の調整（低粒度が多く却下されている場合）
    granularity_counts = patterns.get("granularity_counts", {})
    if granularity_counts.get("low", 0) > granularity_counts.get("high", 0) * 2:
        config["min_granularity"] = "medium"

    # 禁止時間帯の更新（却下が多い時間帯）
    hour_counts = patterns.get("hour_counts", {})
    if hour_counts:
        max_rejection_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
        # その時間帯±1時間を禁止
        banned_ranges = config.get("banned_time_ranges", [])
        start_hour = max(0, max_rejection_hour - 1)
        end_hour = min(23, max_rejection_hour + 1)
        banned_ranges.append({
            "start": f"{start_hour:02d}:00",
            "end": f"{end_hour:02d}:00",
        })
        config["banned_time_ranges"] = banned_ranges

    return config


def get_category_alternative(category: str, rejections: List[Dict[str, Any]]) -> Optional[str]:
    """カテゴリの代替案を取得"""
    config = load_quality_config()

    # 同じカテゴリで却下された回数
    category_rejections = [r for r in rejections if r["category"] == category]

    if len(category_rejections) >= config.get("rejection_threshold", 3):
        # 代替カテゴリを提案
        alternatives = config.get("category_alternatives", {}).get(category, [])

        for alt in alternatives:
            # その代替カテゴリで却下が少ないか確認
            alt_rejections = [r for r in rejections if r["category"] == alt]
            if len(alt_rejections) < len(category_rejections):
                return alt

    return None


def should_change_category(category: str, rejections: List[Dict[str, Any]]) -> bool:
    """カテゴリを変更すべきか判定"""
    config = load_quality_config()
    category_rejections = [r for r in rejections if r["category"] == category]

    return len(category_rejections) >= config.get("rejection_threshold", 3)


if __name__ == "__main__":
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("System 3 ToDo Quality Improvement")
    print("=" * 60)
    print()

    # 却下履歴の分析
    print("[1] Analyzing rejection patterns...")
    rejections = load_rejections(days=30)
    patterns = analyze_rejection_patterns(rejections)

    print(f"    Total rejections: {patterns.get('total_rejections', 0)}")
    print(f"    Top reasons: {list(patterns.get('reason_counts', {}).items())[:3]}")
    print(f"    Top categories: {list(patterns.get('category_counts', {}).items())[:3]}")

    # 品質設定の更新
    print("\n[2] Updating quality config...")
    updated_config = update_quality_config_from_rejections()
    save_quality_config(updated_config)

    print(f"    Banned tags: {updated_config.get('banned_tags', [])}")
    print(f"    Banned categories: {updated_config.get('banned_categories', [])}")
    print(f"    Min granularity: {updated_config.get('min_granularity', 'medium')}")

    print()
