"""
分散実行システム
複数デバイスでのタスク分散実行
"""

import json
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

from manaos_logger import get_logger, get_service_logger

from _paths import UNIFIED_API_PORT

logger = get_service_logger("distributed-execution")


class NodeStatus(Enum):
    """ノードステータス"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"


class DistributedExecution:
    """分散実行システム"""
    
    def __init__(self):
        """初期化"""
        self.nodes = {}
        self.tasks = []
        self.storage_path = Path("distributed_execution_state.json")
        self._load_state()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.nodes = state.get("nodes", {})
                    self.tasks = state.get("tasks", [])
            except (json.JSONDecodeError, IOError):
                self.nodes = {}
                self.tasks = []
        else:
            self.nodes = {}
            self.tasks = []
    
    def _save_state(self):
        """状態を保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "nodes": self.nodes,
                    "tasks": self.tasks,
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"状態保存エラー: {e}")
    
    def register_node(
        self,
        node_id: str,
        url: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        ノードを登録
        
        Args:
            node_id: ノードID
            url: ノードURL
            capabilities: 能力のリスト
            metadata: メタデータ（オプション）
        """
        self.nodes[node_id] = {
            "id": node_id,
            "url": url,
            "capabilities": capabilities,
            "metadata": metadata or {},
            "status": NodeStatus.OFFLINE.value,
            "last_seen": None,
            "current_tasks": []
        }
        self._save_state()
    
    def check_node_status(self, node_id: str) -> bool:
        """
        ノードの状態を確認
        
        Args:
            node_id: ノードID
            
        Returns:
            オンラインの場合True
        """
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        url = node["url"]
        
        try:
            # ヘルスチェックエンドポイントを呼び出し
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                node["status"] = NodeStatus.ONLINE.value
                node["last_seen"] = datetime.now().isoformat()
                self._save_state()
                return True
            else:
                node["status"] = NodeStatus.OFFLINE.value
                self._save_state()
                return False
        except Exception:
            node["status"] = NodeStatus.OFFLINE.value
            self._save_state()
            return False
    
    def find_available_node(self, capability: str) -> Optional[str]:
        """
        利用可能なノードを検索
        
        Args:
            capability: 必要な能力
            
        Returns:
            ノードID（見つかった場合）、None（見つからない場合）
        """
        for node_id, node in self.nodes.items():
            # ステータスを確認
            if self.check_node_status(node_id):
                # 能力を確認
                if capability in node["capabilities"]:
                    # 現在のタスク数を確認
                    if len(node["current_tasks"]) < node["metadata"].get("max_concurrent_tasks", 5):
                        return node_id
        
        return None
    
    def submit_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        preferred_node: Optional[str] = None
    ) -> str:
        """
        タスクを送信
        
        Args:
            task_type: タスクタイプ
            task_data: タスクデータ
            preferred_node: 優先ノード（オプション）
            
        Returns:
            タスクID
        """
        task_id = f"task_{len(self.tasks) + 1}_{int(datetime.now().timestamp())}"
        
        # ノードを選択
        node_id = preferred_node or self.find_available_node(task_type)
        
        if not node_id:
            return None  # type: ignore
        
        task = {
            "id": task_id,
            "type": task_type,
            "data": task_data,
            "node_id": node_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        self.tasks.append(task)
        self.nodes[node_id]["current_tasks"].append(task_id)
        self._save_state()
        
        # ノードにタスクを送信
        try:
            node = self.nodes[node_id]
            response = requests.post(
                f"{node['url']}/api/tasks",
                json={
                    "task_id": task_id,
                    "task_type": task_type,
                    "task_data": task_data
                },
                timeout=30
            )
            
            if response.status_code == 200:
                task["status"] = "running"
                task["started_at"] = datetime.now().isoformat()
                self._save_state()
            else:
                task["status"] = "failed"
                task["error"] = f"HTTP {response.status_code}"
                self._save_state()
        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            self._save_state()
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        タスクの状態を取得
        
        Args:
            task_id: タスクID
            
        Returns:
            タスク情報
        """
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            return None
        
        # ノードから最新の状態を取得
        node_id = task["node_id"]
        if node_id in self.nodes:
            node = self.nodes[node_id]
            try:
                response = requests.get(
                    f"{node['url']}/api/tasks/{task_id}",
                    timeout=10
                )
                if response.status_code == 200:
                    node_status = response.json()
                    task.update(node_status)
                    self._save_state()
            except Exception:
                logger.debug(f"タスク {task_id} の状態更新に失敗")
        
        return task
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        # すべてのノードの状態を確認
        online_nodes = 0
        for node_id in self.nodes.keys():
            if self.check_node_status(node_id):
                online_nodes += 1
        
        return {
            "total_nodes": len(self.nodes),
            "online_nodes": online_nodes,
            "total_tasks": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks if t["status"] == "pending"]),
            "running_tasks": len([t for t in self.tasks if t["status"] == "running"]),
            "completed_tasks": len([t for t in self.tasks if t["status"] == "completed"]),
            "failed_tasks": len([t for t in self.tasks if t["status"] == "failed"]),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("分散実行システムテスト")
    print("=" * 60)
    
    distributed = DistributedExecution()
    
    # ノードを登録（サンプル）
    print("\nノードを登録中...")
    distributed.register_node(
        node_id="node1",
        url=f"http://127.0.0.1:{UNIFIED_API_PORT}",
        capabilities=["image_generation", "model_search"],
        metadata={"max_concurrent_tasks": 3}
    )
    
    # ノードの状態を確認
    print("\nノードの状態を確認中...")
    status = distributed.check_node_status("node1")
    print(f"ノード1の状態: {'オンライン' if status else 'オフライン'}")
    
    # 状態を表示
    system_status = distributed.get_status()
    print(f"\nシステム状態:")
    print(f"  総ノード数: {system_status['total_nodes']}")
    print(f"  オンラインノード数: {system_status['online_nodes']}")


if __name__ == "__main__":
    main()




















