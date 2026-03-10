#!/usr/bin/env python3
"""
学習レイヤー → 記憶系 連携モジュール
学習結果を記憶システムに送信
"""

import sys
import json
import logging
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, '/root/scripts')
sys.path.insert(0, '/root/manaos_learning')

import importlib.util

# learning_api
spec1 = importlib.util.spec_from_file_location("learning_api", "/root/scripts/learning_api.py")
learning_api = importlib.util.module_from_spec(spec1)  # type: ignore
spec1.loader.exec_module(learning_api)  # type: ignore[union-attr]

get_statistics = learning_api.get_statistics
get_recent_examples = learning_api.get_recent_examples
extract_patterns = learning_api.extract_patterns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LearningToMemoryBridge:
    """学習レイヤーから記憶系へのブリッジ"""

    def __init__(self):
        """初期化"""
        self.memory_api_url = self._detect_memory_system()
        self.enabled = self.memory_api_url is not None

        if self.enabled:
            logger.info(f"✅ 記憶システム連携: {self.memory_api_url}")
        else:
            logger.warning("⚠️ 記憶システムが見つかりません（連携無効）")

    def _detect_memory_system(self) -> Optional[str]:
        """記憶システムのURLを検出"""
        # ポート情報ファイルを確認
        port_info_file = Path('/root/.mana_vault/memory_system_port.json')
        if port_info_file.exists():
            try:
                with open(port_info_file, 'r') as f:
                    info = json.load(f)
                    port = info.get('port')
                    if port:
                        return f"http://localhost:{port}"
            except Exception:
                pass

        # フォールバック: よく使われるポートを確認
        for port in [5055, 5054, 5056]:
            try:
                response = httpx.get(f"http://localhost:{port}/health", timeout=1)
                if response.status_code == 200:
                    return f"http://localhost:{port}"
            except Exception:
                continue

        return None

    def send_learning_pattern_to_memory(
        self,
        tool: str,
        pattern: Dict[str, Any],
        pattern_type: str = "correction_pattern"
    ) -> bool:
        """
        学習パターンを記憶システムに送信

        Args:
            tool: ツール名
            pattern: パターン情報
            pattern_type: パターンタイプ（correction_pattern, improvement_pattern等）

        Returns:
            成功したかどうか
        """
        if not self.enabled:
            return False

        try:
            # 記憶システムの形式に変換
            memory_entry = {
                "type": "learning_pattern",
                "subtype": pattern_type,
                "tool": tool,
                "pattern": pattern.get('pattern', pattern.get('description', '')),
                "occurrences": pattern.get('occurrences', 0),
                "confidence": pattern.get('confidence', 0.0),
                "metadata": {
                    "source": "manaos_learning_layer",
                    "extracted_at": datetime.now().isoformat(),
                    "rule_id": pattern.get('id'),
                },
                "tags": [f"learning:{tool}", pattern_type, "auto_extracted"]
            }

            # 記憶システムに送信
            response = httpx.post(
                f"{self.memory_api_url}/api/memory/ingest",
                json=memory_entry,
                timeout=5
            )

            if response.status_code in [200, 201]:
                logger.info(f"✅ 学習パターンを記憶システムに送信: {tool}/{pattern_type}")
                return True
            else:
                logger.warning(f"⚠️ 記憶システム送信失敗: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ 記憶システム連携エラー: {e}")
            return False

    def send_correction_to_memory(
        self,
        tool: str,
        task: str,
        raw_output: str,
        corrected_output: str,
        feedback: str = "good"
    ) -> bool:
        """
        修正履歴を記憶システムに送信

        Args:
            tool: ツール名
            task: タスク名
            raw_output: 元の出力
            corrected_output: 修正後の出力
            feedback: フィードバック

        Returns:
            成功したかどうか
        """
        if not self.enabled:
            return False

        try:
            # 記憶システムの形式に変換
            memory_entry = {
                "type": "correction",
                "tool": tool,
                "task": task,
                "raw": raw_output[:500],  # 長すぎる場合は切り詰め
                "corrected": corrected_output[:500],
                "feedback": feedback,
                "metadata": {
                    "source": "manaos_learning_layer",
                    "timestamp": datetime.now().isoformat(),
                },
                "tags": [f"correction:{tool}", task, feedback]
            }

            # 記憶システムに送信
            response = httpx.post(
                f"{self.memory_api_url}/api/memory/ingest",
                json=memory_entry,
                timeout=5
            )

            if response.status_code in [200, 201]:
                logger.debug(f"✅ 修正履歴を記憶システムに送信: {tool}/{task}")
                return True
            else:
                logger.warning(f"⚠️ 記憶システム送信失敗: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ 記憶システム連携エラー: {e}")
            return False

    def sync_extracted_patterns(self, tool: str, min_occurrences: int = 3) -> int:
        """
        抽出されたパターンを記憶システムに同期

        Args:
            tool: ツール名
            min_occurrences: 最小出現回数

        Returns:
            同期したパターン数
        """
        if not self.enabled:
            return 0

        try:
            patterns = extract_patterns(tool, min_occurrences=min_occurrences, limit=50)
            synced_count = 0

            for pattern in patterns:
                if self.send_learning_pattern_to_memory(tool, pattern, "correction_pattern"):
                    synced_count += 1

            logger.info(f"✅ {synced_count}/{len(patterns)}件のパターンを記憶システムに同期")
            return synced_count

        except Exception as e:
            logger.error(f"❌ パターン同期エラー: {e}")
            return 0


# グローバルインスタンス
_bridge_instance: Optional[LearningToMemoryBridge] = None


def get_memory_bridge() -> LearningToMemoryBridge:
    """記憶ブリッジのシングルトンインスタンスを取得"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = LearningToMemoryBridge()
    return _bridge_instance


def sync_learning_to_memory(tool: Optional[str] = None, auto: bool = True) -> Dict[str, Any]:
    """
    学習レイヤーの結果を記憶システムに同期

    Args:
        tool: 特定ツールのみ同期（Noneなら全ツール）
        auto: 自動同期モード（Trueなら定期的に実行）

    Returns:
        同期結果
    """
    bridge = get_memory_bridge()

    if not bridge.enabled:
        return {
            "status": "disabled",
            "message": "記憶システムが見つかりません"
        }

    result = {
        "status": "success",
        "synced_patterns": 0,
        "tools": []
    }

    if tool:
        tools = [tool]
    else:
        # 全ツールを取得
        stats = get_statistics()
        # ツールリストは統計から取得（簡易実装）
        tools = ["pdf_excel", "daily_report", "summary_bot", "scheduler"]

    for t in tools:
        count = bridge.sync_extracted_patterns(t, min_occurrences=3)
        if count > 0:
            result["synced_patterns"] += count
            result["tools"].append(t)

    return result


if __name__ == "__main__":
    # テスト実行
    print("🔗 学習レイヤー → 記憶系 連携テスト")
    print("=" * 60)

    bridge = get_memory_bridge()
    print(f"状態: {'✅ 有効' if bridge.enabled else '⛔ 無効'}")

    if bridge.enabled:
        result = sync_learning_to_memory()
        print(f"同期結果: {result}")








