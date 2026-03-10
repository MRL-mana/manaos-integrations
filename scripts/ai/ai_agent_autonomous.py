"""
AIエージェント自律実行システム
目標設定と自動実行、長期的なタスク管理
"""

import json
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

try:
    from langchain_integration import LangChainIntegration
except (ImportError, NameError):
    LangChainIntegration = None
from crewai_integration import CrewAIIntegration
from mem0_integration import Mem0Integration
from workflow_automation import WorkflowAutomation


class TaskStatus(Enum):
    """タスクステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class AutonomousAgent:
    """自律エージェント"""
    
    def __init__(self, name: str = "ManaOS Agent"):
        """
        初期化
        
        Args:
            name: エージェント名
        """
        self.name = name
        self.langchain = LangChainIntegration() if LangChainIntegration else None
        self.crewai = CrewAIIntegration()
        self.mem0 = Mem0Integration()
        self.workflow = WorkflowAutomation()
        
        self.tasks = []
        self.goals = []
        self.storage_path = Path("autonomous_agent_state.json")
        self._load_state()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.tasks = state.get("tasks", [])
                    self.goals = state.get("goals", [])
            except Exception:
                self.tasks = []
                self.goals = []
        else:
            self.tasks = []
            self.goals = []
    
    def _save_state(self, max_retries: int = 3):
        """状態を保存（リトライ機能付き）"""
        for attempt in range(max_retries):
            try:
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = self.storage_path.with_suffix('.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "tasks": self.tasks,
                        "goals": self.goals,
                        "last_updated": datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
                temp_path.replace(self.storage_path)
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"状態保存エラー（{max_retries}回リトライ後）: {e}")
                else:
                    import time
                    time.sleep(0.1 * (attempt + 1))
    
    def set_goal(self, goal: str, deadline: Optional[datetime] = None) -> str:
        """
        目標を設定
        
        Args:
            goal: 目標の説明
            deadline: 期限（オプション）
            
        Returns:
            目標ID
        """
        goal_id = f"goal_{len(self.goals) + 1}_{int(time.time())}"
        
        self.goals.append({
            "id": goal_id,
            "goal": goal,
            "deadline": deadline.isoformat() if deadline else None,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "tasks": []
        })
        
        self._save_state()
        
        # 目標をMem0に保存
        if self.mem0.is_available():
            self.mem0.add_memory(
                memory_text=f"目標設定: {goal}",
                user_id="mana",
                metadata={
                    "type": "goal",
                    "goal_id": goal_id,
                    "deadline": deadline.isoformat() if deadline else None
                }
            )
        
        return goal_id
    
    def add_task(
        self,
        description: str,
        goal_id: Optional[str] = None,
        priority: int = 5,
        estimated_time: Optional[int] = None
    ) -> str:
        """
        タスクを追加
        
        Args:
            description: タスクの説明
            goal_id: 関連する目標ID（オプション）
            priority: 優先度（1-10）
            estimated_time: 推定時間（分）
            
        Returns:
            タスクID
        """
        task_id = f"task_{len(self.tasks) + 1}_{int(time.time())}"
        
        task = {
            "id": task_id,
            "description": description,
            "goal_id": goal_id,
            "priority": priority,
            "estimated_time": estimated_time,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        self.tasks.append(task)
        
        if goal_id:
            for goal in self.goals:
                if goal["id"] == goal_id:
                    goal["tasks"].append(task_id)
                    break
        
        self._save_state()
        return task_id
    
    def plan_tasks(self, goal_id: str) -> List[Dict[str, Any]]:
        """
        タスクを計画
        
        Args:
            goal_id: 目標ID
            
        Returns:
            計画されたタスクのリスト
        """
        goal = next((g for g in self.goals if g["id"] == goal_id), None)
        if not goal:
            return []
        
        if not self.langchain.is_available():  # type: ignore[union-attr]
            return []
        
        # LangChainでタスクを計画
        prompt = f"""
目標: {goal['goal']}

この目標を達成するための具体的なタスクを計画してください。
各タスクは明確で実行可能なものにしてください。
タスクは優先順位順に並べてください。

出力形式:
1. タスク1の説明
2. タスク2の説明
...
"""
        
        response = self.langchain.chat(prompt, system_prompt="あなたは優秀なタスクプランナーです。")  # type: ignore[union-attr]
        
        # レスポンスを解析してタスクを作成
        planned_tasks = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                task_desc = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                if task_desc:
                    task_id = self.add_task(task_desc, goal_id=goal_id)
                    planned_tasks.append({"id": task_id, "description": task_desc})
        
        return planned_tasks
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """
        タスクを実行
        
        Args:
            task_id: タスクID
            
        Returns:
            実行結果
        """
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            return {"error": "タスクが見つかりません"}
        
        if task["status"] != TaskStatus.PENDING.value:
            return {"error": f"タスクは既に{task['status']}です"}
        
        task["status"] = TaskStatus.RUNNING.value
        task["started_at"] = datetime.now().isoformat()
        self._save_state()
        
        try:
            # タスクの説明を解析して実行
            description = task["description"]
            
            # ワークフローを実行する場合
            if "画像生成" in description or "generate" in description.lower():
                result = self._execute_image_generation_task(description)
            elif "検索" in description or "search" in description.lower():
                result = self._execute_search_task(description)
            elif "ダウンロード" in description or "download" in description.lower():
                result = self._execute_download_task(description)
            else:
                # 一般的なタスクはLangChainで処理
                result = self._execute_general_task(description)
            
            task["status"] = TaskStatus.COMPLETED.value
            task["completed_at"] = datetime.now().isoformat()
            task["result"] = result
            
        except Exception as e:
            task["status"] = TaskStatus.FAILED.value
            task["error"] = str(e)
            result = {"error": str(e)}
        
        self._save_state()
        return result
    
    def _execute_image_generation_task(self, description: str) -> Dict[str, Any]:
        """画像生成タスクを実行"""
        # プロンプトを抽出
        if self.langchain.is_available():  # type: ignore[union-attr]
            prompt = self.langchain.chat(  # type: ignore[union-attr]
                f"以下のタスクから画像生成のプロンプトを抽出してください: {description}",
                system_prompt="画像生成プロンプトを抽出してください。"
            )
        else:
            prompt = description
        
        result = self.workflow.execute_workflow("generate_and_backup", {
            "prompt": prompt,
            "width": 512,
            "height": 512
        })
        
        return result
    
    def _execute_search_task(self, description: str) -> Dict[str, Any]:
        """検索タスクを実行"""
        # 検索クエリを抽出
        if self.langchain.is_available():  # type: ignore[union-attr]
            query = self.langchain.chat(  # type: ignore[union-attr]
                f"以下のタスクから検索クエリを抽出してください: {description}",
                system_prompt="検索クエリを抽出してください。"
            )
        else:
            query = description
        
        result = self.workflow.execute_workflow("search_and_memorize", {
            "query": query,
            "limit": 10
        })
        
        return result
    
    def _execute_download_task(self, description: str) -> Dict[str, Any]:
        """ダウンロードタスクを実行"""
        # モデルIDを抽出
        import re
        model_ids = re.findall(r'\d+', description)
        
        if model_ids:
            from enhanced_civitai_downloader import EnhancedCivitaiDownloader
            downloader = EnhancedCivitaiDownloader()
            result = downloader.download_with_enhancements(model_ids[0])
            return result
        else:
            return {"error": "モデルIDが見つかりません"}
    
    def _execute_general_task(self, description: str) -> Dict[str, Any]:
        """一般的なタスクを実行"""
        if self.langchain.is_available():  # type: ignore[union-attr]
            response = self.langchain.chat(  # type: ignore[union-attr]
                f"以下のタスクを実行してください: {description}",
                system_prompt="タスクを実行し、結果を報告してください。"
            )
            return {"response": response}
        else:
            return {"error": "LangChainが利用できません"}
    
    def run_autonomous_loop(self, max_iterations: int = 10):
        """
        自律実行ループ
        
        Args:
            max_iterations: 最大反復回数
        """
        print(f"{self.name} 自律実行ループを開始...")
        
        for iteration in range(max_iterations):
            print(f"\n反復 {iteration + 1}/{max_iterations}")
            
            # 実行可能なタスクを取得
            pending_tasks = [t for t in self.tasks if t["status"] == TaskStatus.PENDING.value]
            
            if not pending_tasks:
                print("実行可能なタスクがありません。")
                break
            
            # 優先度順にソート
            pending_tasks.sort(key=lambda x: x["priority"], reverse=True)
            
            # 最初のタスクを実行
            task = pending_tasks[0]
            print(f"タスク実行: {task['description']}")
            
            result = self.execute_task(task["id"])
            print(f"結果: {result}")
            
            # 少し待機
            time.sleep(2)
        
        print("\n自律実行ループ終了")
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "name": self.name,
            "goals_count": len(self.goals),
            "tasks_count": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks if t["status"] == TaskStatus.PENDING.value]),
            "running_tasks": len([t for t in self.tasks if t["status"] == TaskStatus.RUNNING.value]),
            "completed_tasks": len([t for t in self.tasks if t["status"] == TaskStatus.COMPLETED.value]),
            "failed_tasks": len([t for t in self.tasks if t["status"] == TaskStatus.FAILED.value])
        }


def main():
    """テスト用メイン関数"""
    print("AIエージェント自律実行システムテスト")
    print("=" * 60)
    
    agent = AutonomousAgent("ManaOS Test Agent")
    
    # 目標を設定
    goal_id = agent.set_goal("画像生成の自動化を実現する", deadline=datetime.now() + timedelta(days=7))
    print(f"目標設定: {goal_id}")
    
    # タスクを計画
    planned_tasks = agent.plan_tasks(goal_id)
    print(f"計画されたタスク: {len(planned_tasks)}件")
    
    # 状態を表示
    status = agent.get_status()
    print(f"\n状態: {status}")
    
    # 自律実行ループ（テスト用に1回のみ）
    print("\n自律実行ループを開始（1回のみ）...")
    agent.run_autonomous_loop(max_iterations=1)


if __name__ == "__main__":
    main()



