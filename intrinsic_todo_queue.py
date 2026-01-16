#!/usr/bin/env python3
"""
内発的ToDoキューシステム（承認キュー）
PROPOSED → APPROVED → EXECUTED の状態管理
"""

import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# 統一モジュールのインポート
from manaos_logger import get_logger
from obsidian_integration import ObsidianIntegration

logger = get_logger(__name__)


class TodoState(str, Enum):
    """ToDoの状態"""
    PROPOSED = "PROPOSED"  # 提案
    APPROVED = "APPROVED"  # 承認
    REJECTED = "REJECTED"  # 却下
    EXECUTED = "EXECUTED"  # 実行済
    EXPIRED = "EXPIRED"  # 期限切れ


@dataclass
class IntrinsicTodo:
    """内発的ToDo"""
    id: str
    title: str
    reason: str  # 提案理由
    impact: str  # 影響
    risk: str  # リスクレベル（low/medium/high）
    autonomy_level_required: int  # 必要なAutonomy Level
    estimated_minutes: int  # 推定時間（分）
    tags: List[str]  # タグ
    state: TodoState = TodoState.PROPOSED
    created_at: str = ""
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class IntrinsicTodoQueue:
    """内発的ToDoキュー"""
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        intrinsic_motivation_url: str = "http://localhost:5130"
    ):
        """
        初期化
        
        Args:
            storage_path: 保存パス
            intrinsic_motivation_url: Intrinsic Motivation API URL
        """
        self.storage_path = storage_path or Path(__file__).parent / "intrinsic_todos.json"
        self.intrinsic_motivation_url = intrinsic_motivation_url
        
        # ToDoリスト
        self.todos: List[IntrinsicTodo] = []
        self._load_todos()
        
        logger.info("✅ Intrinsic Todo Queue初期化完了")
    
    def _load_todos(self):
        """ToDoを読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.todos = [
                        IntrinsicTodo(**{**t, "state": TodoState(t["state"])})
                        for t in data.get("todos", [])
                    ]
            except Exception as e:
                logger.warning(f"ToDo読み込みエラー: {e}")
                self.todos = []
        else:
            self.todos = []
        
        # 期限切れチェック（PROPOSEDは24時間でEXPIRED）
        self._check_expired_todos()
        
        # 重複統合
        self._merge_duplicate_todos()
    
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
    
    def _check_expired_todos(self):
        """期限切れToDoをチェック（PROPOSEDは24時間でEXPIRED）"""
        now = datetime.now()
        expired_count = 0
        
        for todo in self.todos:
            if todo.state == TodoState.PROPOSED:
                created_time = datetime.fromisoformat(todo.created_at)
                elapsed_hours = (now - created_time).total_seconds() / 3600
                
                if elapsed_hours >= 24:
                    todo.state = TodoState.EXPIRED
                    expired_count += 1
        
        if expired_count > 0:
            logger.info(f"✅ {expired_count}件のToDoが期限切れになりました")
            self._save_todos()
    
    def _merge_duplicate_todos(self):
        """重複ToDoを統合（同一タイトル/同一タグ）"""
        seen = {}
        merged_count = 0
        
        for todo in self.todos[:]:  # コピーを作成
            if todo.state != TodoState.PROPOSED:
                continue
            
            # キー：タイトル + タグの組み合わせ
            key = (todo.title, tuple(sorted(todo.tags)))
            
            if key in seen:
                # 既存のToDoに統合（より新しい理由を採用）
                existing = seen[key]
                if datetime.fromisoformat(todo.created_at) > datetime.fromisoformat(existing.created_at):
                    existing.reason = todo.reason
                    existing.created_at = todo.created_at
                self.todos.remove(todo)
                merged_count += 1
            else:
                seen[key] = todo
        
        if merged_count > 0:
            logger.info(f"✅ {merged_count}件の重複ToDoを統合しました")
            self._save_todos()
    
    def add_todo(self, todo: IntrinsicTodo) -> IntrinsicTodo:
        """ToDoを追加"""
        self.todos.append(todo)
        self._save_todos()
        logger.info(f"✅ ToDo追加: {todo.id} - {todo.title}")
        return todo
    
    def get_todos(self, state: Optional[TodoState] = None) -> List[IntrinsicTodo]:
        """ToDoリストを取得"""
        if state:
            return [t for t in self.todos if t.state == state]
        return self.todos
    
    def approve_todo(self, todo_id: str) -> bool:
        """ToDoを承認"""
        todo = next((t for t in self.todos if t.id == todo_id), None)
        if not todo:
            return False
        
        if todo.state != TodoState.PROPOSED:
            return False
        
        todo.state = TodoState.APPROVED
        todo.approved_at = datetime.now().isoformat()
        self._save_todos()
        
        # Intrinsic Motivation Systemに記録
        try:
            httpx.post(f"{self.intrinsic_motivation_url}/api/record-metric", json={
                "type": "task_accepted",
                "value": 1
            }, timeout=5)
        except:
            pass
        
        logger.info(f"✅ ToDo承認: {todo_id}")
        return True
    
    def reject_todo(self, todo_id: str, reason: Optional[str] = None) -> bool:
        """ToDoを却下"""
        todo = next((t for t in self.todos if t.id == todo_id), None)
        if not todo:
            return False
        
        if todo.state != TodoState.PROPOSED:
            return False
        
        todo.state = TodoState.REJECTED
        todo.rejected_at = datetime.now().isoformat()
        todo.rejection_reason = reason
        self._save_todos()
        
        # 品質改善ループに記録
        try:
            from todo_quality_improvement import record_rejection
            # granularityはestimated_minutesから推定（30分未満=high, 30-120分=medium, 120分以上=low）
            estimated = getattr(todo, 'estimated_minutes', 60)
            if estimated < 30:
                granularity = "high"
            elif estimated < 120:
                granularity = "medium"
            else:
                granularity = "low"
            
            record_rejection(
                todo_id=todo_id,
                reason=reason or "理由なし",
                category=getattr(todo, 'category', 'unknown'),
                tags=todo.tags or [],
                granularity=granularity,
                rejected_at=datetime.now()
            )
        except Exception as e:
            logger.warning(f"品質改善ループへの記録に失敗: {e}")
        
        logger.info(f"✅ ToDo却下: {todo_id} - {reason}")
        return True
    
    def execute_todo(self, todo_id: str) -> Dict[str, Any]:
        """
        ToDoを実行
        UnifiedOrchestratorを使用して実際のタスクを実行
        
        Args:
            todo_id: ToDo ID
            
        Returns:
            実行結果
        """
        todo = next((t for t in self.todos if t.id == todo_id), None)
        if not todo:
            return {"error": "ToDoが見つかりません"}
        
        if todo.state != TodoState.APPROVED:
            return {"error": f"ToDoは承認されていません（現在の状態: {todo.state.value}）"}
        
        logger.info(f"🚀 ToDo実行開始: {todo_id} - {todo.title}")
        
        execution_result = None
        error_message = None
        
        try:
            # UnifiedOrchestratorを使用してタスクを実行
            try:
                from unified_orchestrator import UnifiedOrchestrator
                orchestrator = UnifiedOrchestrator()
                
                # ToDoのtitleとreasonを組み合わせてタスク説明を作成
                task_description = f"{todo.title}\n\n理由: {todo.reason}\n影響: {todo.impact}"
                
                # タグがあれば追加
                if todo.tags:
                    task_description += f"\nタグ: {', '.join(todo.tags)}"
                
                # 非同期実行
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    orchestrator.execute(task_description)
                )
                
                execution_result = {
                    "success": result.status.value == "completed",
                    "result": asdict(result) if hasattr(result, '__dict__') else str(result),
                    "status": result.status.value if hasattr(result, 'status') else "unknown"
                }
                
            except ImportError:
                # UnifiedOrchestratorが利用できない場合は、manaos_core_apiを使用
                try:
                    import manaos_core_api as manaos
                    
                    # ToDoの内容から適切なアクションを推測
                    task_description = f"{todo.title}\n\n理由: {todo.reason}"
                    
                    # タスクタイプを推測（簡単なキーワードマッチング）
                    if any(keyword in todo.title.lower() for keyword in ["画像", "generate", "image"]):
                        action_type = "generate_image"
                    elif any(keyword in todo.title.lower() for keyword in ["検索", "search"]):
                        action_type = "web_search"
                    elif any(keyword in todo.title.lower() for keyword in ["コード", "code", "script"]):
                        action_type = "code_generation"
                    else:
                        action_type = "llm_call"
                    
                    result = manaos.act(action_type, {
                        "prompt": task_description,
                        "task_type": "automation" if action_type != "llm_call" else "reasoning"
                    })
                    
                    execution_result = {
                        "success": result.get("status") != "error",
                        "result": result,
                        "action_type": action_type
                    }
                    
                except ImportError:
                    # manaos_core_apiも利用できない場合は、直接LLMルーターを使用
                    try:
                        from llm_routing import LLMRouter
                        router = LLMRouter()
                        
                        task_description = f"以下のタスクを実行してください: {todo.title}\n\n理由: {todo.reason}\n影響: {todo.impact}"
                        
                        result = router.route(
                            task_type="automation",
                            prompt=task_description
                        )
                        
                        execution_result = {
                            "success": True,
                            "result": result.get("response", ""),
                            "model": result.get("model", "unknown")
                        }
                    except ImportError:
                        # すべて失敗した場合は、ログのみに記録
                        logger.warning("実行エンジンが利用できません。状態のみを更新します。")
                        execution_result = {
                            "success": False,
                            "error": "実行エンジンが利用できません",
                            "result": None
                        }
            
            # 実行結果に基づいて状態を更新
            if execution_result and execution_result.get("success"):
                todo.state = TodoState.EXECUTED
                todo.executed_at = datetime.now().isoformat()
                logger.info(f"✅ ToDo実行成功: {todo_id}")
            else:
                error_message = execution_result.get("error", "実行に失敗しました") if execution_result else "実行エンジンが利用できません"
                logger.error(f"❌ ToDo実行失敗: {todo_id} - {error_message}")
                # 失敗しても状態は更新しない（再実行可能にする）
                return {
                    "status": "error",
                    "todo_id": todo_id,
                    "error": error_message,
                    "execution_result": execution_result
                }
        
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ ToDo実行エラー: {todo_id} - {error_message}", exc_info=True)
            return {
                "status": "error",
                "todo_id": todo_id,
                "error": error_message
            }
        
        # 状態を保存
        self._save_todos()
        
        # Intrinsic Motivation Systemに記録
        try:
            httpx.post(f"{self.intrinsic_motivation_url}/api/record-metric", json={
                "type": "task_executed",
                "value": 1,
                "todo_id": todo_id,
                "success": execution_result.get("success") if execution_result else False
            }, timeout=5)
        except Exception as e:
            logger.warning(f"Intrinsic Motivation Systemへの記録エラー: {e}")
        
        return {
            "status": "executed",
            "todo_id": todo_id,
            "execution_result": execution_result
        }
    
    def generate_proposals(self, max_proposals: int = 5) -> List[IntrinsicTodo]:
        """
        提案を生成
        
        Args:
            max_proposals: 1日あたりの最大提案数（デフォルト: 5）
        """
        # 今日既に生成された提案数をチェック
        today = date.today().isoformat()
        today_proposals = [
            t for t in self.todos
            if t.state == TodoState.PROPOSED
            and t.created_at.startswith(today)
        ]
        
        if len(today_proposals) >= max_proposals:
            logger.info(f"✅ 本日の提案上限に達しています（{max_proposals}件）")
            return []
        
        proposals = []
        
        # 例: RAG failuresの分析
        proposals.append(IntrinsicTodo(
            id=f"im-{datetime.now().strftime('%Y%m%d')}-0001",
            title="RAG failuresの上位エラー分類を更新",
            reason="過去24hで同種エラーが増加",
            impact="成功率向上/再試行削減",
            risk="low",
            autonomy_level_required=1,
            estimated_minutes=8,
            tags=["maintenance", "rag", "learning"]
        ))
        
        # 提案を追加（上限チェック）
        remaining_slots = max_proposals - len(today_proposals)
        added_proposals = []
        
        for proposal in proposals[:remaining_slots]:
            # 重複チェック
            if not any(t.id == proposal.id for t in self.todos):
                self.add_todo(proposal)
                added_proposals.append(proposal)
        
        # 重複統合を再実行
        self._merge_duplicate_todos()
        
        return added_proposals
    
    def save_approval_list_to_obsidian(self):
        """承認待ちリストをObsidianに保存"""
        proposed_todos = self.get_todos(TodoState.PROPOSED)
        
        if not proposed_todos:
            return
        
        try:
            vault_path = Path.home() / "Documents" / "Obsidian Vault"
            if not vault_path.exists():
                vault_path = Path.home() / "Documents" / "Obsidian"
            if not vault_path.exists():
                return
            
            obsidian = ObsidianIntegration(str(vault_path))
            
            today = date.today().isoformat()
            daily_log_path = vault_path / "ManaOS" / "System" / "Daily" / f"System3_Daily_{today}.md"
            
            approval_section = "\n## 🛂 承認待ち提案（Need Approval）\n\n"
            for todo in proposed_todos:
                approval_section += f"""### {todo.title}

- **ID**: `{todo.id}`
- **理由**: {todo.reason}
- **影響**: {todo.impact}
- **リスク**: {todo.risk}
- **推定時間**: {todo.estimated_minutes}分
- **承認方法**: このファイルに `[APPROVE: {todo.id}]` または `[REJECT: {todo.id}]` を追記

"""
            
            if daily_log_path.exists():
                content = daily_log_path.read_text(encoding="utf-8")
                
                # 既存の承認待ちセクションを置換
                if "## 🛂 承認待ち提案" in content:
                    import re
                    content = re.sub(
                        r"## 🛂 承認待ち提案.*?(?=## |$)",
                        approval_section,
                        content,
                        flags=re.DOTALL
                    )
                else:
                    # セクションがない場合は追加
                    if "## 💡 System 3の自己評価" in content:
                        content = content.replace("## 💡 System 3の自己評価", approval_section + "\n## 💡 System 3の自己評価")
                    else:
                        content += approval_section
                
                daily_log_path.write_text(content, encoding="utf-8")
            
            logger.info(f"✅ 承認待ちリストをObsidianに保存しました: {len(proposed_todos)}件")
            
        except Exception as e:
            logger.warning(f"Obsidian保存エラー: {e}")


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import date

app = Flask(__name__)
CORS(app)

todo_queue = None

def init_todo_queue():
    """ToDoキューを初期化"""
    global todo_queue
    if todo_queue is None:
        todo_queue = IntrinsicTodoQueue()
    return todo_queue

# グローバル変数（healthcheck用）
intrinsic_motivation_url = "http://localhost:5130"

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック（依存サービスも確認）"""
    # 依存サービスのチェック
    dependencies = {
        "intrinsic_motivation": False
    }
    
    try:
        response = httpx.get(f"{intrinsic_motivation_url}/health", timeout=2)
        dependencies["intrinsic_motivation"] = response.status_code == 200
    except:
        pass
    
    all_healthy = all(dependencies.values())
    
    return jsonify({
        "status": "healthy" if all_healthy else "degraded",
        "service": "Intrinsic Todo Queue",
        "dependencies": dependencies
    })

@app.route('/api/todos', methods=['GET'])
def get_todos():
    """ToDoリストを取得"""
    queue = init_todo_queue()
    state = request.args.get('state')
    state_enum = TodoState(state) if state else None
    todos = queue.get_todos(state_enum)
    return jsonify({
        "todos": [asdict(t) for t in todos],
        "count": len(todos)
    })

@app.route('/api/todos/<todo_id>/approve', methods=['POST'])
def approve_todo(todo_id: str):
    """ToDoを承認"""
    queue = init_todo_queue()
    success = queue.approve_todo(todo_id)
    if success:
        return jsonify({"status": "approved", "todo_id": todo_id})
    else:
        return jsonify({"error": "承認に失敗しました"}), 400

@app.route('/api/todos/<todo_id>/reject', methods=['POST'])
def reject_todo(todo_id: str):
    """ToDoを却下（品質改善ループ統合済み）"""
    queue = init_todo_queue()
    data = request.get_json() or {}
    reason = data.get("reason")
    success = queue.reject_todo(todo_id, reason)
    if success:
        return jsonify({"status": "rejected", "todo_id": todo_id})
    else:
        return jsonify({"error": "却下に失敗しました"}), 400

@app.route('/api/todos/<todo_id>/execute', methods=['POST'])
def execute_todo(todo_id: str):
    """ToDoを実行"""
    queue = init_todo_queue()
    result = queue.execute_todo(todo_id)
    return jsonify(result)

@app.route('/api/generate-proposals', methods=['POST'])
def generate_proposals():
    """提案を生成"""
    queue = init_todo_queue()
    proposals = queue.generate_proposals()
    queue.save_approval_list_to_obsidian()
    return jsonify({
        "proposals": [asdict(p) for p in proposals],
        "count": len(proposals)
    })

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """ToDoメトリクスを取得"""
    queue = init_todo_queue()
    
    # 各状態のToDo数を集計
    todos = queue.get_todos()
    counts = {
        "proposed": len([t for t in todos if t.state == TodoState.PROPOSED]),
        "approved": len([t for t in todos if t.state == TodoState.APPROVED]),
        "executed": len([t for t in todos if t.state == TodoState.EXECUTED]),
        "rejected": len([t for t in todos if t.state == TodoState.REJECTED]),
        "expired": len([t for t in todos if t.state == TodoState.EXPIRED])
    }
    
    # メトリクス計算
    total_proposed = counts["proposed"] + counts["approved"] + counts["executed"] + counts["rejected"] + counts["expired"]
    
    approval_rate = 0.0
    if total_proposed > 0:
        approval_rate = (counts["approved"] + counts["executed"]) / total_proposed
    
    execution_rate = 0.0
    if counts["approved"] + counts["executed"] > 0:
        execution_rate = counts["executed"] / (counts["approved"] + counts["executed"])
    
    noise_index = 0.0
    if total_proposed > 0:
        noise_index = (counts["rejected"] + counts["expired"]) / total_proposed
    
    return jsonify({
        "counts": counts,
        "approval_rate": approval_rate,
        "execution_rate": execution_rate,
        "noise_index": noise_index,
        "total": len(todos)
    })

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5134
    logger.info(f"🚀 Intrinsic Todo Queue API Server起動 (ポート: {port})")
    app.run(host="0.0.0.0", port=port, debug=False)

