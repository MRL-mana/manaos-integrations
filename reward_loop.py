#!/usr/bin/env python3
"""
ご褒美ループシステム
一定数のPlaybook昇格で「今日はよく育った」ログを出す
"""

import json
import httpx
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger
from obsidian_integration import ObsidianIntegration

logger = get_logger(__name__)


@dataclass
class RewardEvent:
    """ご褒美イベント"""
    event_id: str
    event_type: str  # "playbook_promoted", "milestone_reached", etc.
    message: str
    achievement_level: str  # "bronze", "silver", "gold", "platinum"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class RewardLoop:
    """ご褒美ループシステム"""

    # 達成レベル
    BRONZE_THRESHOLD = 1  # 1個のPlaybook昇格
    SILVER_THRESHOLD = 5  # 5個のPlaybook昇格
    GOLD_THRESHOLD = 10  # 10個のPlaybook昇格
    PLATINUM_THRESHOLD = 20  # 20個のPlaybook昇格

    def __init__(
        self,
        storage_path: Optional[Path] = None
    ):
        """
        初期化

        Args:
            storage_path: 保存パス
        """
        self.storage_path = storage_path or Path(__file__).parent / "reward_loop.json"

        # イベント履歴
        self.reward_history: List[RewardEvent] = []
        self.playbook_count_history: List[Dict[str, Any]] = []

        # レート制限（1日最大1回のSoft報酬）
        self.last_reward_date: Optional[str] = None
        self._load_data()

        logger.info("✅ Reward Loop System初期化完了")

    def _load_data(self):
        """データを読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.reward_history = [
                        RewardEvent(**e) for e in data.get("rewards", [])
                    ]
                    self.playbook_count_history = data.get("playbook_history", [])
                    self.last_reward_date = data.get("last_reward_date")
            except Exception as e:
                logger.warning(f"データ読み込みエラー: {e}")
                self.reward_history = []
                self.playbook_count_history = []
                self.last_reward_date = None
        else:
            self.reward_history = []
            self.playbook_count_history = []
            self.last_reward_date = None

    def _save_data(self):
        """データを保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "rewards": [asdict(e) for e in self.reward_history],
                    "playbook_history": self.playbook_count_history,
                    "last_reward_date": self.last_reward_date,
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"データ保存エラー: {e}")

    def _count_playbooks(self) -> int:
        """現在のPlaybook数をカウント"""
        try:
            vault_path = Path.home() / "Documents" / "Obsidian Vault"
            if not vault_path.exists():
                vault_path = Path.home() / "Documents" / "Obsidian"
            if not vault_path.exists():
                return 0

            playbooks_dir = vault_path / "ManaOS" / "System" / "Playbooks"
            if not playbooks_dir.exists():
                return 0

            playbook_files = list(playbooks_dir.glob("*.md"))
            return len(playbook_files)
        except:
            return 0

    def check_achievements(
        self,
        learning_system_url: str = "http://localhost:5126",
        metrics_collector_url: str = "http://localhost:5127"
    ) -> Optional[RewardEvent]:
        """
        達成状況をチェックしてご褒美イベントを生成

        Args:
            learning_system_url: Learning System API URL
            metrics_collector_url: Metrics Collector API URL

        Returns:
            ご褒美イベント（達成がない場合はNone）
        """
        current_count = self._count_playbooks()
        today = date.today().isoformat()

        # レート制限チェック（1日最大1回のSoft報酬）- 最初にチェック
        if self.last_reward_date == today:
            logger.debug("本日は既に報酬が発火済みです（レート制限）")
            return None

        # 追加の達成条件をチェック
        hard_success_rate_improvement = False
        failure_patterns_learned = False
        autonomy_tasks_completed = False

        try:
            # Learning Systemから統計を取得
            response = httpx.get(f"{learning_system_url}/api/analyze", timeout=5)
            if response.status_code == 200:
                learning_stats = response.json()
                patterns_learned = learning_stats.get("patterns_learned", 0)
                if patterns_learned >= 3:
                    failure_patterns_learned = True
        except:
            pass

        try:
            # Metrics Collectorから統計を取得
            response = httpx.get(f"{metrics_collector_url}/api/metrics/summary", timeout=5)
            if response.status_code == 200:
                metrics_stats = response.json()
                # TODO: 週次比較で成功率向上をチェック
        except:
            pass

        # 今日のカウントを記録
        today_record = next(
            (r for r in self.playbook_count_history if r.get("date") == today),
            None
        )

        if today_record:
            previous_count = today_record.get("count", 0)
        else:
            # 昨日のカウントを取得
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            yesterday_record = next(
                (r for r in self.playbook_count_history if r.get("date") == yesterday),
                None
            )
            previous_count = yesterday_record.get("count", 0) if yesterday_record else 0

            # 今日の記録を追加
            self.playbook_count_history.append({
                "date": today,
                "count": current_count
            })

        # 増加数を計算
        increase = current_count - previous_count

        if increase <= 0 and not failure_patterns_learned:
            return None

        # 達成レベルを判定
        achievement_level = None
        message = None

        if current_count >= self.PLATINUM_THRESHOLD and previous_count < self.PLATINUM_THRESHOLD:
            achievement_level = "platinum"
            message = f"🎉 プラチナ達成！{self.PLATINUM_THRESHOLD}個のPlaybookが完成しました。System 3は完璧に成長しています！"
        elif current_count >= self.GOLD_THRESHOLD and previous_count < self.GOLD_THRESHOLD:
            achievement_level = "gold"
            message = f"🌟 ゴールド達成！{self.GOLD_THRESHOLD}個のPlaybookが完成しました。System 3は素晴らしく成長しています！"
        elif current_count >= self.SILVER_THRESHOLD and previous_count < self.SILVER_THRESHOLD:
            achievement_level = "silver"
            message = f"✨ シルバー達成！{self.SILVER_THRESHOLD}個のPlaybookが完成しました。System 3は順調に成長しています！"
        elif current_count >= self.BRONZE_THRESHOLD and previous_count < self.BRONZE_THRESHOLD:
            achievement_level = "bronze"
            message = f"🎯 ブロンズ達成！{self.BRONZE_THRESHOLD}個のPlaybookが完成しました。System 3は成長を始めています！"
        elif increase > 0:
            # マイルストーン達成はしていないが、Playbookが増えた
            achievement_level = "growth"
            message = f"📈 今日は{increase}個のPlaybookが追加されました。System 3は着実に成長しています！"
        elif failure_patterns_learned:
            # 失敗パターン学習の達成
            achievement_level = "learning"
            message = f"🧠 失敗パターンを3つ以上学習しました。System 3は失敗から学んでいます！"

        if achievement_level and message:
            event = RewardEvent(
                event_id=f"reward_{int(datetime.now().timestamp())}",
                event_type="playbook_promoted",
                message=message,
                achievement_level=achievement_level
            )

            self.reward_history.append(event)

            # 最新100件のみ保持
            self.reward_history = self.reward_history[-100:]

            # レート制限：本日の日付を記録
            self.last_reward_date = today

            # 保存
            self._save_data()

            # Obsidianに記録
            self._save_to_obsidian(event)

            logger.info(f"✅ ご褒美イベント生成: {achievement_level} - {message}")

            return event

        return None

    def _save_to_obsidian(self, event: RewardEvent):
        """ご褒美イベントをObsidianに保存"""
        try:
            vault_path = Path.home() / "Documents" / "Obsidian Vault"
            if not vault_path.exists():
                vault_path = Path.home() / "Documents" / "Obsidian"
            if not vault_path.exists():
                return

            obsidian = ObsidianIntegration(str(vault_path))

            # 今日のログに追加
            today = date.today().isoformat()
            daily_log_path = vault_path / "ManaOS" / "System" / "Daily" / f"System3_Daily_{today}.md"

            if daily_log_path.exists():
                # 既存のログに追加
                content = daily_log_path.read_text(encoding="utf-8")

                # 「## 💡 System 3の自己評価」セクションを探す
                if "## 💡 System 3の自己評価" in content:
                    # セクションの後に追加
                    content = content.replace(
                        "## 💡 System 3の自己評価",
                        f"## 💡 System 3の自己評価\n\n**{event.message}**\n\n達成レベル: {event.achievement_level.upper()}\n"
                    )
                else:
                    # セクションがない場合は最後に追加
                    content += f"\n\n## 💡 System 3の自己評価\n\n**{event.message}**\n\n達成レベル: {event.achievement_level.upper()}\n"

                daily_log_path.write_text(content, encoding="utf-8")
            else:
                # 新しいログを作成
                content = f"""# System 3 Daily Log: {today}

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Autonomy Level**: Level 1（Internal Maintenance Only）

---

## 💡 System 3の自己評価

**{event.message}**

達成レベル: {event.achievement_level.upper()}

---

**次回更新**: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')} 21:30
"""
                obsidian.create_note(
                    title=f"System3_Daily_{today}",
                    content=content,
                    tags=["ManaOS", "System3", "Daily", "Log", "Reward"],
                    folder="ManaOS/System/Daily"
                )

            logger.info(f"✅ ご褒美イベントをObsidianに保存しました")

        except Exception as e:
            logger.warning(f"Obsidian保存エラー: {e}")

    def get_recent_rewards(self, days: int = 7) -> List[RewardEvent]:
        """直近のご褒美イベントを取得"""
        cutoff_date = (date.today() - timedelta(days=days)).isoformat()
        return [
            e for e in self.reward_history
            if e.timestamp >= cutoff_date
        ]

    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        current_count = self._count_playbooks()
        recent_rewards = self.get_recent_rewards(7)

        return {
            "current_playbook_count": current_count,
            "bronze_threshold": self.BRONZE_THRESHOLD,
            "silver_threshold": self.SILVER_THRESHOLD,
            "gold_threshold": self.GOLD_THRESHOLD,
            "platinum_threshold": self.PLATINUM_THRESHOLD,
            "recent_rewards_count": len(recent_rewards),
            "recent_rewards": [asdict(e) for e in recent_rewards],
            "timestamp": datetime.now().isoformat()
        }


# Flask APIサーバー
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

reward_loop = None

def init_reward_loop():
    """ご褒美ループシステムを初期化"""
    global reward_loop
    if reward_loop is None:
        reward_loop = RewardLoop()
    return reward_loop

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Reward Loop System"})

@app.route('/api/check', methods=['POST'])
def check_achievements():
    """達成状況をチェック"""
    loop = init_reward_loop()
    event = loop.check_achievements(
        learning_system_url="http://localhost:5126",
        metrics_collector_url="http://localhost:5127"
    )

    if event:
        return jsonify({
            "achievement": True,
            "event": asdict(event)
        })
    else:
        return jsonify({
            "achievement": False,
            "message": "新しい達成はありません"
        })

@app.route('/api/status', methods=['GET'])
def get_status():
    """状態を取得"""
    loop = init_reward_loop()
    return jsonify(loop.get_status())

@app.route('/api/recent', methods=['GET'])
def get_recent():
    """直近のご褒美を取得"""
    loop = init_reward_loop()
    days = int(request.args.get('days', 7))
    rewards = loop.get_recent_rewards(days)
    return jsonify({
        "rewards": [asdict(e) for e in rewards],
        "count": len(rewards)
    })

if __name__ == "__main__":
    from flask import request
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5133
    logger.info(f"🚀 Reward Loop API Server起動 (ポート: {port})")
    app.run(host="0.0.0.0", port=port, debug=False)
