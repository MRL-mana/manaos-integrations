#!/usr/bin/env python3
"""
学習レイヤー → 人格系 連携モジュール
学習結果を人格システムに反映
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.insert(0, '/root/scripts')
sys.path.insert(0, '/root/manaos_learning')

import importlib.util

# learning_api
spec1 = importlib.util.spec_from_file_location("learning_api", "/root/scripts/learning_api.py")
learning_api = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(learning_api)

get_statistics = learning_api.get_statistics


def send_learning_insights_to_personality(insights: Dict[str, Any]) -> bool:
    """
    学習インサイトを人格システムに送信

    Args:
        insights: 学習インサイト（ツール別の改善傾向など）

    Returns:
        成功したかどうか
    """
    try:
        # 人格進化トラッカーに送信
        personality_path = Path("/root/manaos_unified_system/services/personality_evolution_tracker.py")
        if not personality_path.exists():
            return False

        # 人格システムのログ形式に変換
        evolution_entry = {
            "event_type": "learning_insight",
            "data": {
                "insights": insights,
                "timestamp": datetime.now().isoformat(),
                "source": "manaos_learning_layer"
            }
        }

        # 人格進化ログに追記
        evolution_log = Path("/root/.mana_vault/personality_evolution/evolution_log.jsonl")
        evolution_log.parent.mkdir(parents=True, exist_ok=True)

        with open(evolution_log, 'a') as f:
            f.write(json.dumps(evolution_entry, ensure_ascii=False) + '\n')

        return True
    except Exception as e:
        print(f"❌ 人格システム連携エラー: {e}")
        return False


def analyze_learning_trends() -> Dict[str, Any]:
    """学習トレンドを分析して人格システムに送信"""
    stats = get_statistics()

    insights = {
        "total_learning_events": stats.get("total", 0),
        "correction_rate": (
            stats.get("with_correction", 0) / stats.get("total", 1) * 100
            if stats.get("total", 0) > 0 else 0
        ),
        "feedback_quality": {
            "good": stats.get("feedback_good", 0),
            "bad": stats.get("feedback_bad", 0),
        },
        "timestamp": datetime.now().isoformat()
    }

    return insights


if __name__ == "__main__":
    print("🧠 学習レイヤー → 人格系 連携テスト")
    print("=" * 60)

    insights = analyze_learning_trends()
    print(f"分析結果: {insights}")

    if send_learning_insights_to_personality(insights):
        print("✅ 人格システムに送信成功")
    else:
        print("⚠️ 人格システムへの送信失敗（システムが見つかりません）")








