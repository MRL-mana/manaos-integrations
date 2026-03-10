#!/usr/bin/env python3
"""
双方向連携モジュール
各システム ↔ 学習系の双方向連携を実現
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

sys.path.insert(0, '/root/scripts')
sys.path.insert(0, '/root/manaos_learning')

import importlib.util

# learning_api
spec1 = importlib.util.spec_from_file_location("learning_api", "/root/scripts/learning_api.py")
learning_api = importlib.util.module_from_spec(spec1)  # type: ignore
spec1.loader.exec_module(learning_api)  # type: ignore[union-attr]

log_event = learning_api.log_event
get_statistics = learning_api.get_statistics
get_recent_examples = learning_api.get_recent_examples

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BidirectionalBridge:
    """双方向連携ブリッジ"""

    def __init__(self):
        """初期化"""
        self.memory_bridge = self._load_memory_bridge()
        self.personality_bridge = self._load_personality_bridge()
        self.autonomous_bridge = self._load_autonomous_bridge()
        self.backup_bridge = self._load_backup_bridge()

    def _load_memory_bridge(self):
        """記憶系ブリッジをロード"""
        try:
            spec = importlib.util.spec_from_file_location(
                "memory_integration",
                "/root/manaos_learning/memory_integration.py"
            )
            memory_module = importlib.util.module_from_spec(spec)  # type: ignore
            spec.loader.exec_module(memory_module)  # type: ignore[union-attr]
            return memory_module.get_memory_bridge()
        except Exception as e:
            logger.warning(f"記憶系ブリッジのロード失敗: {e}")
            return None

    def _load_personality_bridge(self):
        """人格系ブリッジをロード"""
        try:
            spec = importlib.util.spec_from_file_location(
                "personality_integration",
                "/root/manaos_learning/personality_integration.py"
            )
            personality_module = importlib.util.module_from_spec(spec)  # type: ignore
            spec.loader.exec_module(personality_module)  # type: ignore[union-attr]
            return personality_module
        except Exception as e:
            logger.warning(f"人格系ブリッジのロード失敗: {e}")
            return None

    def _load_autonomous_bridge(self):
        """自律系ブリッジをロード"""
        try:
            spec = importlib.util.spec_from_file_location(
                "autonomous_integration",
                "/root/manaos_learning/autonomous_integration.py"
            )
            autonomous_module = importlib.util.module_from_spec(spec)  # type: ignore
            spec.loader.exec_module(autonomous_module)  # type: ignore[union-attr]
            return autonomous_module
        except Exception as e:
            logger.warning(f"自律系ブリッジのロード失敗: {e}")
            return None

    def _load_backup_bridge(self):
        """バックアップ系ブリッジをロード"""
        try:
            spec = importlib.util.spec_from_file_location(
                "backup_integration",
                "/root/manaos_learning/backup_integration.py"
            )
            backup_module = importlib.util.module_from_spec(spec)  # type: ignore
            spec.loader.exec_module(backup_module)  # type: ignore[union-attr]
            return backup_module
        except Exception as e:
            logger.warning(f"バックアップ系ブリッジのロード失敗: {e}")
            return None

    # === 記憶系 → 学習系（逆方向）===

    def fetch_memory_patterns_to_learning(self, tool: Optional[str] = None) -> int:
        """
        記憶系から学習パターンを取得して学習レイヤーに反映

        Args:
            tool: 特定ツールのみ（Noneなら全ツール）

        Returns:
            取得したパターン数
        """
        if not self.memory_bridge or not self.memory_bridge.enabled:
            logger.warning("記憶系ブリッジが無効です")
            return 0

        try:
            # Weaviateから学習パターンを取得
            import httpx
            memory_url = self.memory_bridge.memory_api_url

            # クエリ構築
            query = {
                "query": {
                    "Get": {
                        "Class": "LearningPattern",
                        "where": {
                            "path": ["type"],
                            "operator": "Equal",
                            "valueString": "learning_pattern"
                        },
                        "limit": 50
                    }
                }
            }

            if tool:
                query["query"]["Get"]["where"] = {
                    "operator": "And",
                    "operands": [
                        {
                            "path": ["type"],
                            "operator": "Equal",
                            "valueString": "learning_pattern"
                        },
                        {
                            "path": ["tool"],
                            "operator": "Equal",
                            "valueString": tool
                        }
                    ]
                }

            response = httpx.post(
                f"{memory_url}/v1/graphql",
                json=query,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                patterns = data.get("data", {}).get("Get", {}).get("LearningPattern", [])

                # 学習レイヤーに記録
                count = 0
                for pattern in patterns:
                    # 学習レイヤーにパターンを記録
                    log_event(
                        tool=pattern.get("tool", "unknown"),
                        task="pattern_sync_from_memory",
                        phase="sync",
                        input_data={"pattern_id": pattern.get("id")},
                        raw_output=pattern.get("pattern", ""),
                        tags=["memory_sync", "pattern"],
                        meta={
                            "source": "weaviate",
                            "occurrences": pattern.get("occurrences", 0),
                            "confidence": pattern.get("confidence", 0.0)
                        }
                    )
                    count += 1

                logger.info(f"✅ 記憶系から{count}件のパターンを学習レイヤーに同期")
                return count
            else:
                logger.warning(f"記憶系クエリ失敗: {response.status_code}")
                return 0

        except Exception as e:
            logger.error(f"記憶系 → 学習系同期エラー: {e}")
            return 0

    # === 人格系 → 学習系（逆方向）===

    def fetch_personality_insights_to_learning(self) -> int:
        """
        人格系からインサイトを取得して学習レイヤーに反映

        Returns:
            取得したインサイト数
        """
        if not self.personality_bridge:
            logger.warning("人格系ブリッジが無効です")
            return 0

        try:
            # 進化ログからインサイトを取得
            evolution_log = Path("/root/.mana_vault/personality_evolution/evolution_log.jsonl")
            if not evolution_log.exists():
                return 0

            count = 0
            with open(evolution_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("event_type") == "learning_insight":
                            # 学習レイヤーに記録
                            insights = entry.get("data", {}).get("insights", {})
                            log_event(
                                tool="personality_system",
                                task="insight_sync_from_personality",
                                phase="sync",
                                input_data={"event_type": "learning_insight"},
                                raw_output=json.dumps(insights, ensure_ascii=False),
                                tags=["personality_sync", "insight"],
                                meta={
                                    "source": "personality_evolution",
                                    "timestamp": entry.get("data", {}).get("timestamp")
                                }
                            )
                            count += 1
                    except json.JSONDecodeError:
                        continue

            if count > 0:
                logger.info(f"✅ 人格系から{count}件のインサイトを学習レイヤーに同期")
            return count

        except Exception as e:
            logger.error(f"人格系 → 学習系同期エラー: {e}")
            return 0

    # === 自律系 → 学習系（逆方向）===

    def fetch_autonomous_decisions_to_learning(self) -> int:
        """
        自律系から判断履歴を取得して学習レイヤーに反映

        Returns:
            取得した判断数
        """
        if not self.autonomous_bridge:
            logger.warning("自律系ブリッジが無効です")
            return 0

        try:
            # 学習ログから自律系の記録を取得
            log_file = Path("/root/manaos_learning/learning_log.jsonl")
            if not log_file.exists():
                return 0

            count = 0
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        meta = record.get("meta", {})
                        if meta.get("source") == "autonomous_engine":
                            # 既に記録されているので、統計として集計
                            count += 1
                    except json.JSONDecodeError:
                        continue

            if count > 0:
                logger.info(f"✅ 自律系から{count}件の判断履歴を確認")
            return count

        except Exception as e:
            logger.error(f"自律系 → 学習系同期エラー: {e}")
            return 0

    # === 全システム双方向同期 ===

    def sync_all_bidirectional(self) -> Dict[str, Any]:
        """
        全システムの双方向同期を実行

        Returns:
            同期結果
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "memory_to_learning": 0,
            "personality_to_learning": 0,
            "autonomous_to_learning": 0,
            "status": "success"
        }

        try:
            # 記憶系 → 学習系
            result["memory_to_learning"] = self.fetch_memory_patterns_to_learning()

            # 人格系 → 学習系
            result["personality_to_learning"] = self.fetch_personality_insights_to_learning()

            # 自律系 → 学習系
            result["autonomous_to_learning"] = self.fetch_autonomous_decisions_to_learning()

            logger.info(f"✅ 双方向同期完了: {result}")

        except Exception as e:
            logger.error(f"双方向同期エラー: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result


# グローバルインスタンス
_bridge_instance: Optional[BidirectionalBridge] = None


def get_bidirectional_bridge() -> BidirectionalBridge:
    """双方向ブリッジのシングルトンインスタンスを取得"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = BidirectionalBridge()
    return _bridge_instance


def sync_all_systems() -> Dict[str, Any]:
    """全システムの双方向同期を実行（便利関数）"""
    bridge = get_bidirectional_bridge()
    return bridge.sync_all_bidirectional()


if __name__ == "__main__":
    print("🔄 双方向連携テスト")
    print("=" * 60)

    bridge = get_bidirectional_bridge()
    result = bridge.sync_all_bidirectional()

    print(f"結果: {json.dumps(result, indent=2, ensure_ascii=False)}")








