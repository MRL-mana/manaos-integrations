#!/usr/bin/env python3
"""
⚙️ ManaOS 自己管理システム
設定の自動管理、リソースの自動管理
"""

import json
import psutil
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_service_logger("self-management-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SelfManagementSystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("SelfManagementSystem")


@dataclass
class ManagementAction:
    """管理アクション"""
    action_id: str
    action_type: str  # "config_update", "resource_cleanup", "service_restart", "optimization"
    description: str
    target: str
    executed_at: str
    result: Dict[str, Any]


class SelfManagementSystem:
    """自己管理システム"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path or Path(__file__).parent / "self_management_config.json"
        self.config = self._load_config()
        
        # 管理アクション履歴
        self.actions: List[ManagementAction] = []
        self.actions_storage = Path("management_actions.json")
        self._load_actions()
        
        # リソース監視
        self.resource_history: List[Dict[str, Any]] = []
        self.resource_storage = Path("resource_history.json")
        self._load_resource_history()
        
        # コールバック関数
        self.on_resource_managed = None
        
        logger.info("✅ Self Management System初期化完了")
    
    def execute_security_action(self, threat: Dict[str, Any]) -> Dict[str, Any]:
        """
        セキュリティアクションを実行（自己保護システムとの連携）
        
        Args:
            threat: 脅威情報
            
        Returns:
            実行結果
        """
        try:
            # 脅威の重大度に応じたアクションを実行
            severity = threat.get("severity", "low")
            threat_type = threat.get("threat_type", "")
            
            actions = []
            
            if severity in ["high", "critical"]:
                # 高リスク脅威の場合、リソースを制限
                actions.append("resource_limit")
                # 設定を一時的に変更
                actions.append("config_lockdown")
            
            # 管理アクションを記録
            action = ManagementAction(
                action_id=f"security_{int(time.time())}",
                action_type="security_action",
                description=f"セキュリティアクション実行: {threat_type} ({severity})",
                target=threat.get("source", ""),
                executed_at=datetime.now().isoformat(),
                result={"success": True, "actions": actions, "threat": threat}
            )
            self.actions.append(action)
            self._save_actions()
            
            return {"success": True, "actions": actions}
        except Exception as e:
            return {"error": str(e)}
    
    def record_improvement_suggestion(self, improvement: Dict[str, Any]) -> Dict[str, Any]:
        """
        改善提案を記録（自己進化システムとの連携）
        
        Args:
            improvement: 改善提案情報
            
        Returns:
            記録結果
        """
        try:
            # 改善提案を管理アクションとして記録
            action = ManagementAction(
                action_id=f"improvement_{int(time.time())}",
                action_type="optimization",
                description=f"改善提案: {improvement.get('description', '')}",
                target=improvement.get("file_path", ""),
                executed_at=datetime.now().isoformat(),
                result={"improvement": improvement}
            )
            self.actions.append(action)
            self._save_actions()
            
            return {"success": True, "message": "改善提案を記録しました"}
        except Exception as e:
            return {"error": str(e)}
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"設定読み込みエラー: {e}")
        
        return {
            "enable_auto_config_management": True,
            "enable_auto_resource_management": True,
            "resource_cleanup_interval_minutes": 60,
            "config_backup_enabled": True,
            "max_resource_usage_percent": 85
        }
    
    def _load_actions(self):
        """管理アクション履歴を読み込む"""
        if self.actions_storage.exists():
            try:
                with open(self.actions_storage, 'r', encoding='utf-8') as f:
                    actions_data = json.load(f)
                    self.actions = [
                        ManagementAction(**item) for item in actions_data
                    ]
            except Exception as e:
                logger.warning(f"管理アクション履歴読み込みエラー: {e}")
    
    def _save_actions(self):
        """管理アクション履歴を保存"""
        try:
            actions_data = [asdict(action) for action in self.actions[-100:]]
            with open(self.actions_storage, 'w', encoding='utf-8') as f:
                json.dump(actions_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"管理アクション履歴保存エラー: {e}")
    
    def _load_resource_history(self):
        """リソース履歴を読み込む"""
        if self.resource_storage.exists():
            try:
                with open(self.resource_storage, 'r', encoding='utf-8') as f:
                    self.resource_history = json.load(f)
            except Exception as e:
                logger.warning(f"リソース履歴読み込みエラー: {e}")
    
    def _save_resource_history(self):
        """リソース履歴を保存"""
        try:
            # 最新100件のみ保存
            recent_history = self.resource_history[-100:]
            with open(self.resource_storage, 'w', encoding='utf-8') as f:
                json.dump(recent_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"リソース履歴保存エラー: {e}")
    
    def manage_config(self, config_path: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        設定を管理
        
        Args:
            config_path: 設定ファイルのパス
            updates: 更新内容
            
        Returns:
            管理結果
        """
        if not self.config.get("enable_auto_config_management", True):
            return {"skipped": True, "reason": "自動設定管理が無効です"}
        
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                return {"error": f"設定ファイルが見つかりません: {config_path}"}
            
            # バックアップ作成
            if self.config.get("config_backup_enabled", True):
                backup_path = f"{config_path}.backup.{int(time.time())}"
                import shutil
                shutil.copy(config_path, backup_path)
            
            # 設定を読み込み
            with open(config_file, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
            
            # 設定を更新
            updated_config = {**current_config, **updates}
            
            # 設定を保存
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(updated_config, f, ensure_ascii=False, indent=2)
            
            # 管理アクションを記録
            action = ManagementAction(
                action_id=f"config_{int(time.time())}",
                action_type="config_update",
                description=f"設定を更新: {config_path}",
                target=config_path,
                executed_at=datetime.now().isoformat(),
                result={"success": True, "updates": updates}
            )
            self.actions.append(action)
            self._save_actions()
            
            return {"success": True, "message": f"設定を更新しました: {config_path}"}
        except Exception as e:
            return {"error": str(e)}
    
    def manage_resources(self) -> Dict[str, Any]:
        """
        リソースを管理
        
        Returns:
            管理結果
        """
        if not self.config.get("enable_auto_resource_management", True):
            return {"skipped": True, "reason": "自動リソース管理が無効です"}
        
        try:
            # リソース使用率を取得
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            resource_usage = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "timestamp": datetime.now().isoformat()
            }
            
            # リソース履歴に記録
            self.resource_history.append(resource_usage)
            self._save_resource_history()
            
            # リソース使用率が閾値を超えている場合
            max_usage = self.config.get("max_resource_usage_percent", 85)
            actions_taken = []
            
            if memory.percent > max_usage:
                # メモリ使用率が高い場合
                import gc
                gc.collect()
                actions_taken.append("memory_cleanup")
            
            if disk.percent > max_usage:
                # ディスク使用率が高い場合
                # 一時ファイルのクリーンアップ
                temp_paths = [Path("data/temp"), Path("data/cache"), Path("logs")]
                for temp_path in temp_paths:
                    if temp_path.exists():
                        import shutil
                        for item in temp_path.iterdir():
                            if item.is_file():
                                # 7日以上古いファイルを削除
                                file_age = datetime.now() - datetime.fromtimestamp(item.stat().st_mtime)
                                if file_age > timedelta(days=7):
                                    item.unlink()
                actions_taken.append("disk_cleanup")
            
            # 管理アクションを記録
            if actions_taken:
                action = ManagementAction(
                    action_id=f"resource_{int(time.time())}",
                    action_type="resource_cleanup",
                    description="リソースクリーンアップを実行",
                    target="system",
                    executed_at=datetime.now().isoformat(),
                    result={"success": True, "actions": actions_taken, "resource_usage": resource_usage}
                )
                self.actions.append(action)
                self._save_actions()
            
            return {
                "success": True,
                "resource_usage": resource_usage,
                "actions_taken": actions_taken
            }
        except Exception as e:
            return {"error": str(e)}
    
    def optimize_config(self, config_path: str) -> Dict[str, Any]:
        """
        設定を最適化
        
        Args:
            config_path: 設定ファイルのパス
            
        Returns:
            最適化結果
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                return {"error": f"設定ファイルが見つかりません: {config_path}"}
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 設定の最適化（簡易版）
            optimizations = []
            
            # タイムアウト設定の最適化
            if "timeout" in config:
                current_timeout = config["timeout"]
                if current_timeout > 300:  # 5分以上の場合
                    config["timeout"] = 300
                    optimizations.append("タイムアウト設定を最適化しました")
            
            # キャッシュ設定の最適化
            if "cache_size" in config:
                current_cache_size = config["cache_size"]
                if current_cache_size > 1000:  # 1000件以上の場合
                    config["cache_size"] = 1000
                    optimizations.append("キャッシュサイズを最適化しました")
            
            # 最適化された設定を保存
            if optimizations:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                # 管理アクションを記録
                action = ManagementAction(
                    action_id=f"optimize_{int(time.time())}",
                    action_type="optimization",
                    description=f"設定を最適化: {config_path}",
                    target=config_path,
                    executed_at=datetime.now().isoformat(),
                    result={"success": True, "optimizations": optimizations}
                )
                self.actions.append(action)
                self._save_actions()
            
            return {
                "success": True,
                "optimizations": optimizations,
                "config": config
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_resource_trends(self) -> Dict[str, Any]:
        """
        リソーストレンドを取得
        
        Returns:
            トレンド分析結果
        """
        if not self.resource_history:
            return {"error": "リソース履歴がありません"}
        
        recent_history = self.resource_history[-50:]
        
        cpu_values = [h.get("cpu_percent", 0) for h in recent_history]
        memory_values = [h.get("memory_percent", 0) for h in recent_history]
        disk_values = [h.get("disk_percent", 0) for h in recent_history]
        
        return {
            "cpu": {
                "average": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "min": min(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "trend": "improving" if len(cpu_values) > 1 and cpu_values[-1] < cpu_values[0] else "degrading"
            },
            "memory": {
                "average": sum(memory_values) / len(memory_values) if memory_values else 0,
                "min": min(memory_values) if memory_values else 0,
                "max": max(memory_values) if memory_values else 0,
                "trend": "improving" if len(memory_values) > 1 and memory_values[-1] < memory_values[0] else "degrading"
            },
            "disk": {
                "average": sum(disk_values) / len(disk_values) if disk_values else 0,
                "min": min(disk_values) if disk_values else 0,
                "max": max(disk_values) if disk_values else 0,
                "trend": "improving" if len(disk_values) > 1 and disk_values[-1] < disk_values[0] else "degrading"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def auto_optimize_resources(self) -> Dict[str, Any]:
        """
        リソースを自動最適化
        
        Returns:
            最適化結果
        """
        if not self.config.get("enable_auto_resource_management", True):
            return {"skipped": True, "reason": "自動リソース管理が無効です"}
        
        try:
            # リソース管理を実行
            resource_result = self.manage_resources()
            
            # 最適化アクションを記録
            action = ManagementAction(
                action_id=f"auto_optimize_{int(time.time())}",
                action_type="optimization",
                description="リソース自動最適化",
                target="system",
                executed_at=datetime.now().isoformat(),
                result=resource_result
            )
            self.actions.append(action)
            self._save_actions()
            
            return {
                "success": True,
                "message": "リソース自動最適化を実行しました",
                "result": resource_result
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        # 最近のアクションの分析
        recent_actions = [
            action for action in self.actions
            if datetime.fromisoformat(action.executed_at) > datetime.now() - timedelta(hours=24)
        ]
        
        # アクションタイプ別の統計
        action_stats = {}
        for action in recent_actions:
            action_type = action.action_type
            action_stats[action_type] = action_stats.get(action_type, 0) + 1
        
        return {
            "actions_count": len(self.actions),
            "recent_actions_count": len(recent_actions),
            "resource_history_count": len(self.resource_history),
            "auto_config_management_enabled": self.config.get("enable_auto_config_management", True),
            "auto_resource_management_enabled": self.config.get("enable_auto_resource_management", True),
            "config_backup_enabled": self.config.get("config_backup_enabled", True),
            "action_statistics": action_stats,
            "config": self.config,
            "resource_trends": self.get_resource_trends(),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    system = SelfManagementSystem()
    
    # テスト: リソース管理
    result = system.manage_resources()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # テスト: 状態取得
    status = system.get_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

