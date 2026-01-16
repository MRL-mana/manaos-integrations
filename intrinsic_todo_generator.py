#!/usr/bin/env python3
"""
内発ToDoの半自動生成システム
「今週やると一番効く改善」Top3を生成
"""

import json
import httpx
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger
from obsidian_integration import ObsidianIntegration

logger = get_logger(__name__)


@dataclass
class IntrinsicTodo:
    """内発的ToDo"""
    todo_id: str
    title: str
    description: str
    impact_score: float  # 影響スコア（0-100）
    effort_score: float  # 工数スコア（0-100、低いほど簡単）
    priority: int  # 優先度（1-10）
    category: str  # カテゴリ
    estimated_hours: float  # 推定時間（時間）
    requires_approval: bool  # 承認が必要か
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def efficiency_score(self) -> float:
        """効率スコア（影響/工数）"""
        if self.effort_score == 0:
            return 0.0
        return self.impact_score / self.effort_score


class IntrinsicTodoGenerator:
    """内発的ToDo生成システム"""

    def __init__(
        self,
        learning_system_url: str = "http://localhost:5126",
        metrics_collector_url: str = "http://localhost:5127",
        task_critic_url: str = "http://localhost:5102",
        storage_path: Optional[Path] = None
    ):
        """
        初期化

        Args:
            learning_system_url: Learning System API URL
            metrics_collector_url: Metrics Collector API URL
            task_critic_url: Task Critic API URL
            storage_path: 保存パス
        """
        self.learning_system_url = learning_system_url
        self.metrics_collector_url = metrics_collector_url
        self.task_critic_url = task_critic_url
        self.storage_path = storage_path or Path(__file__).parent / "intrinsic_todos.json"

        # ToDoリスト
        self.todos: List[IntrinsicTodo] = []
        self._load_todos()

        logger.info("✅ Intrinsic Todo Generator初期化完了")

    def _load_todos(self):
        """ToDoを読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.todos = [
                        IntrinsicTodo(**t) for t in data.get("todos", [])
                    ]
            except Exception as e:
                logger.warning(f"ToDo読み込みエラー: {e}")
                self.todos = []
        else:
            self.todos = []

    def _save_todos(self):
        """ToDoを保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "todos": [asdict(t) for t in self.todos],
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"ToDo保存エラー: {e}")

    def analyze_improvement_opportunities(self) -> List[IntrinsicTodo]:
        """
        改善機会を分析してToDoを生成

        Returns:
            生成されたToDoのリスト
        """
        todos = []

        try:
            # Learning Systemから統計を取得
            learning_response = httpx.get(f"{self.learning_system_url}/api/analyze", timeout=5)
            learning_stats = learning_response.json() if learning_response.status_code == 200 else {}

            # Metrics Collectorから統計を取得
            metrics_response = httpx.get(f"{self.metrics_collector_url}/api/metrics/summary", timeout=5)
            metrics_stats = metrics_response.json() if metrics_response.status_code == 200 else {}

            success_rate = metrics_stats.get("success_rate", 0.0)
            error_rate = metrics_stats.get("error_rate", 0.0)
            avg_response_time = metrics_stats.get("avg_response_time", 0.0)
            patterns_learned = learning_stats.get("patterns_learned", 0)

            # 改善機会1: 成功率向上
            if success_rate < 0.8:
                todos.append(IntrinsicTodo(
                    todo_id=f"todo_success_rate_{int(datetime.now().timestamp())}",
                    title="成功率向上のための改善",
                    description=f"現在の成功率は{success_rate:.1%}です。失敗パターンを分析し、成功率を80%以上に向上させましょう。",
                    impact_score=90.0,
                    effort_score=60.0,
                    priority=9,
                    category="Performance",
                    estimated_hours=4.0,
                    requires_approval=False
                ))

            # 改善機会2: エラー率削減
            if error_rate > 0.1:
                todos.append(IntrinsicTodo(
                    todo_id=f"todo_error_rate_{int(datetime.now().timestamp())}",
                    title="エラー率削減",
                    description=f"現在のエラー率は{error_rate:.1%}です。エラーログを分析し、再発防止策を実装しましょう。",
                    impact_score=85.0,
                    effort_score=50.0,
                    priority=8,
                    category="Reliability",
                    estimated_hours=3.0,
                    requires_approval=False
                ))

            # 改善機会3: レスポンス時間改善
            if avg_response_time > 2000:  # 2秒以上
                todos.append(IntrinsicTodo(
                    todo_id=f"todo_response_time_{int(datetime.now().timestamp())}",
                    title="レスポンス時間の改善",
                    description=f"現在の平均レスポンス時間は{avg_response_time:.0f}msです。ボトルネックを特定し、最適化しましょう。",
                    impact_score=75.0,
                    effort_score=70.0,
                    priority=7,
                    category="Performance",
                    estimated_hours=5.0,
                    requires_approval=False
                ))

            # 改善機会4: パターン学習の強化
            if patterns_learned < 10:
                todos.append(IntrinsicTodo(
                    todo_id=f"todo_pattern_learning_{int(datetime.now().timestamp())}",
                    title="パターン学習の強化",
                    description=f"現在の学習パターン数は{patterns_learned}です。成功パターンを抽出し、Playbook化を進めましょう。",
                    impact_score=80.0,
                    effort_score=40.0,
                    priority=8,
                    category="Learning",
                    estimated_hours=2.0,
                    requires_approval=False
                ))

            # 改善機会5: Playbookの整理
            playbooks_count = self._count_playbooks()
            if playbooks_count > 0:
                todos.append(IntrinsicTodo(
                    todo_id=f"todo_playbook_org_{int(datetime.now().timestamp())}",
                    title="Playbookの整理と最適化",
                    description=f"現在{playbooks_count}個のPlaybookがあります。使用頻度を分析し、不要なものを整理しましょう。",
                    impact_score=60.0,
                    effort_score=30.0,
                    priority=6,
                    category="Organization",
                    estimated_hours=1.5,
                    requires_approval=False
                ))

        except Exception as e:
            logger.warning(f"改善機会分析エラー: {e}")

        # 効率スコアでソート
        todos.sort(key=lambda t: t.efficiency_score, reverse=True)

        # Top 3を返す
        return todos[:3]

    def _count_playbooks(self) -> int:
        """Playbook数をカウント"""
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

    def generate_weekly_top3(self) -> List[IntrinsicTodo]:
        """
        今週のTop 3 ToDoを生成

        Returns:
            Top 3 ToDoのリスト
        """
        todos = self.analyze_improvement_opportunities()

        # 既存のToDoとマージ
        self.todos.extend(todos)

        # 重複を削除（同じタイトルのもの）
        seen_titles = set()
        unique_todos = []
        for todo in self.todos:
            if todo.title not in seen_titles:
                seen_titles.add(todo.title)
                unique_todos.append(todo)

        self.todos = unique_todos

        # 効率スコアでソート
        self.todos.sort(key=lambda t: t.efficiency_score, reverse=True)

        # 保存
        self._save_todos()

        # Top 3を返す
        return self.todos[:3]

    def save_to_obsidian(self, todos: List[IntrinsicTodo]):
        """ToDoをObsidianに保存"""
        try:
            vault_path = Path.home() / "Documents" / "Obsidian Vault"
            if not vault_path.exists():
                vault_path = Path.home() / "Documents" / "Obsidian"
            if not vault_path.exists():
                return

            obsidian = ObsidianIntegration(str(vault_path))

            content = f"""# 今週のTop 3 改善ToDo

**生成日**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**期間**: 今週

---

"""

            for i, todo in enumerate(todos, 1):
                content += f"""## {i}. {todo.title}

**影響スコア**: {todo.impact_score:.1f}/100
**工数スコア**: {todo.effort_score:.1f}/100
**効率スコア**: {todo.efficiency_score:.2f}
**優先度**: {todo.priority}/10
**推定時間**: {todo.estimated_hours:.1f}時間
**承認必要**: {'はい' if todo.requires_approval else 'いいえ'}

### 説明

{todo.description}

### カテゴリ

{todo.category}

---

"""

            content += f"""
## 実行方法

1. 各ToDoを確認
2. 承認が必要な場合は承認を取得
3. 実行を開始
4. 完了後に結果を記録

---

**次回更新**: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}
"""

            obsidian.create_note(
                title=f"Intrinsic_Todos_Week_{date.today().isocalendar()[1]}",
                content=content,
                tags=["ManaOS", "System3", "Intrinsic", "Todo"],
                folder="ManaOS/System/Todos"
            )

            logger.info(f"✅ ToDoをObsidianに保存しました: {len(todos)}件")

        except Exception as e:
            logger.warning(f"Obsidian保存エラー: {e}")


# Flask APIサーバー
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

todo_generator = None

def init_todo_generator():
    """ToDo生成システムを初期化"""
    global todo_generator
    if todo_generator is None:
        todo_generator = IntrinsicTodoGenerator()
    return todo_generator

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Intrinsic Todo Generator"})

@app.route('/api/generate-top3', methods=['POST'])
def generate_top3():
    """Top 3 ToDoを生成"""
    generator = init_todo_generator()
    todos = generator.generate_weekly_top3()

    # Obsidianに保存
    generator.save_to_obsidian(todos)

    return jsonify({
        "todos": [asdict(t) for t in todos],
        "count": len(todos)
    })

@app.route('/api/todos', methods=['GET'])
def get_todos():
    """ToDoリストを取得"""
    generator = init_todo_generator()
    return jsonify({
        "todos": [asdict(t) for t in generator.todos],
        "count": len(generator.todos)
    })

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5132
    logger.info(f"🚀 Intrinsic Todo Generator API Server起動 (ポート: {port})")
    app.run(host="0.0.0.0", port=port, debug=False)
