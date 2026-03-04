#!/usr/bin/env python3
"""
ManaOS Computer Use System - Multi-PC Manager (準備版)
複数のPCで並列実行するための基盤
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import requests

logger = logging.getLogger(__name__)


@dataclass
class PCNode:
    """PC ノード情報"""
    host: str
    port: int
    name: str
    auth_token: Optional[str] = None
    enabled: bool = True
    
    def get_base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    def health_check(self) -> bool:
        """ヘルスチェック"""
        try:
            headers = {}
            if self.auth_token:
                headers['X-Auth-Token'] = self.auth_token
            
            response = requests.get(
                f"{self.get_base_url()}/health",
                headers=headers,
                timeout=3.0
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed for {self.name}: {e}")
            return False


class MultiPCManager:
    """
    マルチPC管理（準備版）
    
    将来: 複数のX280/PCで並列タスク実行
    現状: 基盤のみ実装、設定ファイル読み込み
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: PC設定ファイルのパス
        """
        self.config_path = config_path or Path("/root/manaos_computer_use/multi_pc_config.json")
        self.nodes: List[PCNode] = []
        
        if self.config_path.exists():
            self._load_config()
    
    def _load_config(self) -> None:
        """設定ファイルを読み込み"""
        import json
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            for node_data in config.get("nodes", []):
                node = PCNode(**node_data)
                self.nodes.append(node)
            
            logger.info(f"Loaded {len(self.nodes)} PC nodes")
        
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    def save_config(self) -> None:
        """設定ファイルを保存"""
        import json
        
        config = {
            "nodes": [
                {
                    "host": node.host,
                    "port": node.port,
                    "name": node.name,
                    "auth_token": node.auth_token,
                    "enabled": node.enabled
                }
                for node in self.nodes
            ]
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Config saved: {self.config_path}")
    
    def add_node(
        self,
        host: str,
        port: int,
        name: str,
        auth_token: Optional[str] = None
    ) -> PCNode:
        """PCノードを追加"""
        node = PCNode(
            host=host,
            port=port,
            name=name,
            auth_token=auth_token
        )
        
        self.nodes.append(node)
        self.save_config()
        
        logger.info(f"Added PC node: {name} ({host}:{port})")
        return node
    
    def get_online_nodes(self) -> List[PCNode]:
        """オンラインのノード一覧"""
        online = []
        
        for node in self.nodes:
            if not node.enabled:
                continue
            
            if node.health_check():
                online.append(node)
                logger.info(f"✅ {node.name}: online")
            else:
                logger.warning(f"❌ {node.name}: offline")
        
        return online
    
    def distribute_tasks(
        self,
        tasks: List[str],
        strategy: str = "round_robin"
    ) -> Dict[str, List[str]]:
        """
        タスクを各PCに分散
        
        Args:
            tasks: タスクリスト
            strategy: 分散戦略（round_robin, least_loaded, etc.）
        
        Returns:
            Dict[str, List[str]]: {node_name: [tasks]}
        """
        online_nodes = self.get_online_nodes()
        
        if not online_nodes:
            logger.error("No online nodes available")
            return {}
        
        distribution = {node.name: [] for node in online_nodes}
        
        if strategy == "round_robin":
            # ラウンドロビン
            for i, task in enumerate(tasks):
                node = online_nodes[i % len(online_nodes)]
                distribution[node.name].append(task)
        
        elif strategy == "least_loaded":
            # TODO: 負荷を監視して最も空いているノードに割り当て
            # 今回はラウンドロビンと同じ
            for i, task in enumerate(tasks):
                node = online_nodes[i % len(online_nodes)]
                distribution[node.name].append(task)
        
        return distribution
    
    @staticmethod
    def create_sample_config() -> None:
        """サンプル設定ファイルを作成"""
        config = {
            "nodes": [
                {
                    "host": "100.127.121.20",
                    "port": 5009,
                    "name": "X280_Primary",
                    "auth_token": "your_token_here",
                    "enabled": True
                },
                {
                    "host": "100.127.121.21",
                    "port": 5009,
                    "name": "X280_Secondary",
                    "auth_token": "your_token_here",
                    "enabled": False
                }
            ]
        }
        
        config_path = Path("/root/manaos_computer_use/multi_pc_config.json")
        
        import json
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Sample config created: {config_path}")
        print("   Edit this file to add your PC nodes")


# ===== テスト用 =====

if __name__ == "__main__":
    print("🖥️ Multi-PC Manager - Setup")
    print("=" * 60)
    
    # サンプル設定作成
    if not Path("/root/manaos_computer_use/multi_pc_config.json").exists():
        print("\n📝 Creating sample config...")
        MultiPCManager.create_sample_config()
    
    # マネージャー初期化
    manager = MultiPCManager()
    
    print(f"\n📋 Configured nodes: {len(manager.nodes)}")
    for node in manager.nodes:
        print(f"  - {node.name}: {node.host}:{node.port} (enabled: {node.enabled})")
    
    # オンラインチェック
    print("\n🔍 Checking online nodes...")
    online = manager.get_online_nodes()
    
    print(f"\n✅ Online nodes: {len(online)}/{len(manager.nodes)}")
    
    # タスク分散デモ
    if online:
        tasks = ["task1", "task2", "task3", "task4", "task5"]
        distribution = manager.distribute_tasks(tasks)
        
        print("\n📊 Task distribution (round-robin):")
        for node_name, task_list in distribution.items():
            print(f"  {node_name}: {len(task_list)} tasks")
            for task in task_list:
                print(f"    - {task}")
    
    print("\n✅ Setup completed")

