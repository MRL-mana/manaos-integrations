#!/usr/bin/env python3
"""
🔧 ManaOS 包括的自己能力システム
自己修復、自己学習、自己最適化、自己診断、自律システムを統合
"""

import os
import json
import time
import psutil
import subprocess
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("ComprehensiveSelfCapabilities")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("ComprehensiveSelfCapabilities")

# 依存モジュール（オプション）
try:
    from learning_system import LearningSystem
    LEARNING_SYSTEM_AVAILABLE = True
except ImportError:
    LEARNING_SYSTEM_AVAILABLE = False
    LearningSystem = None

try:
    from auto_optimization import AutoOptimization
    AUTO_OPTIMIZATION_AVAILABLE = True
except ImportError:
    AUTO_OPTIMIZATION_AVAILABLE = False
    AutoOptimization = None

try:
    from predictive_maintenance import PredictiveMaintenance
    PREDICTIVE_MAINTENANCE_AVAILABLE = True
except ImportError:
    PREDICTIVE_MAINTENANCE_AVAILABLE = False
    PredictiveMaintenance = None

try:
    from autonomy_system import AutonomySystem
    AUTONOMY_SYSTEM_AVAILABLE = True
except ImportError:
    AUTONOMY_SYSTEM_AVAILABLE = False
    AutonomySystem = None

try:
    from self_evolution_system import SelfEvolutionSystem
    SELF_EVOLUTION_AVAILABLE = True
except ImportError:
    SELF_EVOLUTION_AVAILABLE = False
    SelfEvolutionSystem = None

try:
    from self_protection_system import SelfProtectionSystem
    SELF_PROTECTION_AVAILABLE = True
except ImportError:
    SELF_PROTECTION_AVAILABLE = False
    SelfProtectionSystem = None

try:
    from self_management_system import SelfManagementSystem
    SELF_MANAGEMENT_AVAILABLE = True
except ImportError:
    SELF_MANAGEMENT_AVAILABLE = False
    SelfManagementSystem = None


class ErrorPattern:
    """エラーパターン"""
    
    def __init__(self, error_type: str, error_message: str, context: Dict[str, Any]):
        self.error_type = error_type
        self.error_message = error_message
        self.context = context
        self.occurrence_count = 1
        self.first_seen = datetime.now().isoformat()
        self.last_seen = datetime.now().isoformat()
        self.successful_fixes = []
        self.failed_fixes = []
    
    def record_occurrence(self):
        """発生を記録"""
        self.occurrence_count += 1
        self.last_seen = datetime.now().isoformat()
    
    def record_fix_attempt(self, fix_action: str, success: bool):
        """修復試行を記録"""
        if success:
            self.successful_fixes.append({
                "action": fix_action,
                "timestamp": datetime.now().isoformat()
            })
        else:
            self.failed_fixes.append({
                "action": fix_action,
                "timestamp": datetime.now().isoformat()
            })


class RepairAction:
    """修復アクション"""
    
    def __init__(self, name: str, action_func: Callable, priority: int = 5):
        self.name = name
        self.action_func = action_func
        self.priority = priority
        self.success_count = 0
        self.failure_count = 0
        self.last_executed = None
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """修復アクションを実行"""
        try:
            result = self.action_func(context)
            self.success_count += 1
            self.last_executed = datetime.now().isoformat()
            return {
                "success": True,
                "result": result,
                "action": self.name
            }
        except Exception as e:
            self.failure_count += 1
            self.last_executed = datetime.now().isoformat()
            return {
                "success": False,
                "error": str(e),
                "action": self.name
            }
    
    def get_success_rate(self) -> float:
        """成功率を取得"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total


class ComprehensiveSelfCapabilitiesSystem:
    """包括的自己能力システム"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path or Path(__file__).parent / "comprehensive_self_capabilities_config.json"
        self.config = self._load_config()
        
        # エラーパターンの学習
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.error_patterns_storage = Path("error_patterns.json")
        self._load_error_patterns()
        
        # 修復アクション
        self.repair_actions: List[RepairAction] = []
        self._initialize_repair_actions()
        
        # 依存システム
        self.learning_system = None
        if LEARNING_SYSTEM_AVAILABLE:
            try:
                self.learning_system = LearningSystem()
            except Exception as e:
                logger.warning(f"Learning System初期化エラー: {e}")
        
        self.auto_optimization = None
        if AUTO_OPTIMIZATION_AVAILABLE:
            try:
                self.auto_optimization = AutoOptimization()
            except Exception as e:
                logger.warning(f"Auto Optimization初期化エラー: {e}")
        
        self.predictive_maintenance = None
        if PREDICTIVE_MAINTENANCE_AVAILABLE:
            try:
                self.predictive_maintenance = PredictiveMaintenance()
            except Exception as e:
                logger.warning(f"Predictive Maintenance初期化エラー: {e}")
        
        self.autonomy_system = None
        if AUTONOMY_SYSTEM_AVAILABLE:
            try:
                self.autonomy_system = AutonomySystem()
            except Exception as e:
                logger.warning(f"Autonomy System初期化エラー: {e}")
        
        # 自己進化システム
        self.self_evolution = None
        if SELF_EVOLUTION_AVAILABLE:
            try:
                self.self_evolution = SelfEvolutionSystem()
                logger.info("✅ Self Evolution System初期化完了")
            except Exception as e:
                logger.warning(f"Self Evolution System初期化エラー: {e}")
        
        # 自己保護システム
        self.self_protection = None
        if SELF_PROTECTION_AVAILABLE:
            try:
                self.self_protection = SelfProtectionSystem()
                logger.info("✅ Self Protection System初期化完了")
            except Exception as e:
                logger.warning(f"Self Protection System初期化エラー: {e}")
        
        # 自己管理システム
        self.self_management = None
        if SELF_MANAGEMENT_AVAILABLE:
            try:
                self.self_management = SelfManagementSystem()
                logger.info("✅ Self Management System初期化完了")
            except Exception as e:
                logger.warning(f"Self Management System初期化エラー: {e}")
        
        # 修復履歴
        self.repair_history: deque = deque(maxlen=1000)
        
        # コールバック関数
        self.on_repair_success = None
        
        logger.info("✅ Comprehensive Self Capabilities System初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                schema = {
                    "required": [],
                    "fields": {
                        "enable_auto_repair": {"type": bool, "default": True},
                        "enable_auto_optimization": {"type": bool, "default": True},
                        "enable_auto_adaptation": {"type": bool, "default": True},
                        "repair_threshold": {"type": int, "default": 3},
                        "optimization_interval_minutes": {"type": int, "default": 60}
                    }
                }
                
                is_valid, errors = config_validator.validate_config(config, schema, self.config_path)
                if not is_valid:
                    logger.warning(f"設定ファイル検証エラー: {errors}")
                
                return config
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(self.config_path)},
                    user_message="設定ファイルの読み込みに失敗しました"
                )
                logger.warning(f"設定読み込みエラー: {error.message}")
        
        return {
            "enable_auto_repair": True,
            "enable_auto_optimization": True,
            "enable_auto_adaptation": True,
            "repair_threshold": 3,
            "optimization_interval_minutes": 60
        }
    
    def _load_error_patterns(self):
        """エラーパターンを読み込む"""
        if self.error_patterns_storage.exists():
            try:
                with open(self.error_patterns_storage, 'r', encoding='utf-8') as f:
                    patterns_data = json.load(f)
                    for pattern_id, pattern_data in patterns_data.items():
                        pattern = ErrorPattern(
                            pattern_data["error_type"],
                            pattern_data["error_message"],
                            pattern_data["context"]
                        )
                        pattern.occurrence_count = pattern_data.get("occurrence_count", 1)
                        pattern.first_seen = pattern_data.get("first_seen", datetime.now().isoformat())
                        pattern.last_seen = pattern_data.get("last_seen", datetime.now().isoformat())
                        pattern.successful_fixes = pattern_data.get("successful_fixes", [])
                        pattern.failed_fixes = pattern_data.get("failed_fixes", [])
                        self.error_patterns[pattern_id] = pattern
            except Exception as e:
                logger.warning(f"エラーパターン読み込みエラー: {e}")
    
    def _save_error_patterns(self):
        """エラーパターンを保存"""
        try:
            patterns_data = {}
            for pattern_id, pattern in self.error_patterns.items():
                patterns_data[pattern_id] = {
                    "error_type": pattern.error_type,
                    "error_message": pattern.error_message,
                    "context": pattern.context,
                    "occurrence_count": pattern.occurrence_count,
                    "first_seen": pattern.first_seen,
                    "last_seen": pattern.last_seen,
                    "successful_fixes": pattern.successful_fixes,
                    "failed_fixes": pattern.failed_fixes
                }
            
            with open(self.error_patterns_storage, 'w', encoding='utf-8') as f:
                json.dump(patterns_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"エラーパターン保存エラー: {e}")
    
    def _initialize_repair_actions(self):
        """修復アクションを初期化"""
        # サービス再起動
        self.repair_actions.append(RepairAction(
            "restart_service",
            self._repair_restart_service,
            priority=8
        ))
        
        # キャッシュクリア
        self.repair_actions.append(RepairAction(
            "clear_cache",
            self._repair_clear_cache,
            priority=5
        ))
        
        # プロセス終了
        self.repair_actions.append(RepairAction(
            "kill_process",
            self._repair_kill_process,
            priority=7
        ))
        
        # リソース解放
        self.repair_actions.append(RepairAction(
            "free_resources",
            self._repair_free_resources,
            priority=6
        ))
        
        # 設定リセット
        self.repair_actions.append(RepairAction(
            "reset_config",
            self._repair_reset_config,
            priority=4
        ))
        
        # ネットワーク再接続
        self.repair_actions.append(RepairAction(
            "reconnect_network",
            self._repair_reconnect_network,
            priority=5
        ))
        
        # データベース接続修復
        self.repair_actions.append(RepairAction(
            "repair_database_connection",
            self._repair_database_connection,
            priority=7
        ))
        
        # Obsidian接続修復
        self.repair_actions.append(RepairAction(
            "repair_obsidian_connection",
            self._repair_obsidian_connection,
            priority=6
        ))
        
        # 設定ファイル修復
        self.repair_actions.append(RepairAction(
            "repair_config_file",
            self._repair_config_file,
            priority=5
        ))
        
        # リソース不足修復
        self.repair_actions.append(RepairAction(
            "repair_resource_shortage",
            self._repair_resource_shortage,
            priority=8
        ))
        
        # ネットワークパス切り替え
        self.repair_actions.append(RepairAction(
            "switch_network_path",
            self._repair_switch_network_path,
            priority=6
        ))
        
        # タイムアウト設定調整
        self.repair_actions.append(RepairAction(
            "adjust_timeout",
            self._repair_adjust_timeout,
            priority=4
        ))
    
    def _repair_restart_service(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """サービス再起動修復"""
        service_name = context.get("service_name")
        if not service_name:
            return {"error": "service_nameが必要です"}
        
        try:
            # Windowsサービスの場合
            if subprocess.run(["sc", "query", service_name], capture_output=True).returncode == 0:
                subprocess.run(["sc", "stop", service_name], check=True)
                time.sleep(2)
                subprocess.run(["sc", "start", service_name], check=True)
                return {"success": True, "message": f"{service_name}を再起動しました"}
            
            # systemdサービスの場合
            if subprocess.run(["systemctl", "is-active", service_name], capture_output=True).returncode == 0:
                subprocess.run(["systemctl", "restart", service_name], check=True)
                return {"success": True, "message": f"{service_name}を再起動しました"}
            
            return {"error": f"{service_name}が見つかりません"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_clear_cache(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """キャッシュクリア修復"""
        cache_path = context.get("cache_path", "data/cache")
        try:
            cache_dir = Path(cache_path)
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
                return {"success": True, "message": f"キャッシュをクリアしました: {cache_path}"}
            return {"error": f"キャッシュパスが見つかりません: {cache_path}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_kill_process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """プロセス終了修復"""
        process_name = context.get("process_name")
        pid = context.get("pid")
        
        try:
            if pid:
                process = psutil.Process(pid)
                process.terminate()
                time.sleep(1)
                if process.is_running():
                    process.kill()
                return {"success": True, "message": f"プロセスを終了しました: PID {pid}"}
            elif process_name:
                for proc in psutil.process_iter(['pid', 'name']):
                    if process_name.lower() in proc.info['name'].lower():
                        proc.terminate()
                        time.sleep(1)
                        if proc.is_running():
                            proc.kill()
                return {"success": True, "message": f"プロセスを終了しました: {process_name}"}
            return {"error": "process_nameまたはpidが必要です"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_free_resources(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """リソース解放修復"""
        try:
            # メモリ使用率が高い場合、ガベージコレクションを実行
            import gc
            gc.collect()
            
            # キャッシュをクリア
            if self.auto_optimization:
                self.auto_optimization._clear_cache()
            
            return {"success": True, "message": "リソースを解放しました"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_reset_config(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """設定リセット修復"""
        config_path = context.get("config_path")
        backup_path = context.get("backup_path")
        
        if not config_path:
            return {"error": "config_pathが必要です"}
        
        try:
            config_file = Path(config_path)
            if backup_path and Path(backup_path).exists():
                import shutil
                shutil.copy(backup_path, config_path)
                return {"success": True, "message": f"設定をリセットしました: {config_path}"}
            return {"error": f"バックアップが見つかりません: {backup_path}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_reconnect_network(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """ネットワーク再接続修復"""
        try:
            import socket
            import time
            
            # 接続先URLを取得
            url = context.get("url", "http://localhost:5678")
            host = context.get("host", "localhost")
            port = context.get("port", 5678)
            
            # 接続テスト
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    
                    if result == 0:
                        return {"success": True, "message": f"ネットワーク接続成功: {host}:{port}"}
                    
                    time.sleep(2 ** attempt)  # 指数バックオフ
                except Exception as e:
                    logger.warning(f"接続試行 {attempt + 1}/{max_retries} 失敗: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
            
            return {"error": f"ネットワーク接続に失敗: {host}:{port}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_database_connection(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """データベース接続修復"""
        try:
            db_type = context.get("db_type", "sqlite")
            connection_string = context.get("connection_string")
            
            if db_type == "sqlite":
                db_path = context.get("db_path", "data/memory.db")
                db_file = Path(db_path)
                
                # データベースファイルの存在確認
                if not db_file.exists():
                    # バックアップから復旧を試みる
                    backup_path = Path(f"{db_path}.backup")
                    if backup_path.exists():
                        import shutil
                        shutil.copy(backup_path, db_path)
                        return {"success": True, "message": f"データベースをバックアップから復旧: {db_path}"}
                    else:
                        # 新しいデータベースを作成
                        db_file.parent.mkdir(parents=True, exist_ok=True)
                        db_file.touch()
                        return {"success": True, "message": f"新しいデータベースを作成: {db_path}"}
                
                # データベースの整合性チェック
                try:
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    conn.execute("PRAGMA integrity_check")
                    conn.close()
                    return {"success": True, "message": f"データベース整合性確認OK: {db_path}"}
                except Exception as e:
                    # 整合性エラーの場合、バックアップから復旧
                    backup_path = Path(f"{db_path}.backup")
                    if backup_path.exists():
                        import shutil
                        shutil.copy(backup_path, db_path)
                        return {"success": True, "message": f"データベースをバックアップから復旧（整合性エラー）: {db_path}"}
                    return {"error": f"データベース整合性エラー: {e}"}
            
            elif db_type == "postgresql":
                # PostgreSQL接続の再試行
                if connection_string:
                    try:
                        import psycopg2
                        conn = psycopg2.connect(connection_string)
                        conn.close()
                        return {"success": True, "message": "PostgreSQL接続成功"}
                    except Exception as e:
                        return {"error": f"PostgreSQL接続失敗: {e}"}
            
            return {"error": "データベースタイプが不明です"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_obsidian_connection(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obsidian接続修復"""
        try:
            default_vault = os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault")
            vault_path = context.get("vault_path", default_vault)
            vault_dir = Path(vault_path)
            
            # Vaultの存在確認
            if not vault_dir.exists():
                # 代替パスを試す
                default_vault = os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault")
                alternative_paths = [
                    Path.home() / "OneDrive" / "Desktop" / "Obsidian" / "ManaOS",
                    Path.home() / "Desktop" / "Obsidian" / "ManaOS",
                    Path(default_vault) / "ManaOS" if Path(default_vault).exists() else None,
                    Path(os.getenv("MANAOS_INTEGRATIONS_DIR", r"C:\Users\mana4\Desktop\manaos_integrations")) / "obsidian" / "ManaOS"
                ]
                # Noneを除外
                alternative_paths = [p for p in alternative_paths if p is not None]
                
                for alt_path in alternative_paths:
                    if alt_path.exists():
                        return {
                            "success": True,
                            "message": f"Obsidian Vaultを代替パスで発見: {alt_path}",
                            "new_path": str(alt_path)
                        }
                
                return {"error": f"Obsidian Vaultが見つかりません: {vault_path}"}
            
            # Vaultの書き込み権限確認
            test_file = vault_dir / ".manaos_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                return {"success": True, "message": f"Obsidian Vault接続OK: {vault_path}"}
            except Exception as e:
                return {"error": f"Obsidian Vault書き込み権限エラー: {e}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_config_file(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """設定ファイル修復"""
        try:
            config_path = context.get("config_path")
            if not config_path:
                return {"error": "config_pathが必要です"}
            
            config_file = Path(config_path)
            
            # 設定ファイルの存在確認
            if not config_file.exists():
                # バックアップから復旧
                backup_path = Path(f"{config_path}.backup")
                if backup_path.exists():
                    import shutil
                    shutil.copy(backup_path, config_path)
                    return {"success": True, "message": f"設定ファイルをバックアップから復旧: {config_path}"}
                
                # デフォルト設定を作成
                default_config = context.get("default_config", {})
                if default_config:
                    config_file.parent.mkdir(parents=True, exist_ok=True)
                    import json
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(default_config, f, ensure_ascii=False, indent=2)
                    return {"success": True, "message": f"デフォルト設定ファイルを作成: {config_path}"}
                
                return {"error": f"設定ファイルが見つかりません: {config_path}"}
            
            # 設定ファイルの検証
            try:
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 設定値の検証と自動修正
                default_config = context.get("default_config", {})
                if default_config:
                    modified = False
                    for key, default_value in default_config.items():
                        if key not in config_data:
                            config_data[key] = default_value
                            modified = True
                        elif config_data[key] is None:
                            config_data[key] = default_value
                            modified = True
                    
                    if modified:
                        # バックアップを作成
                        backup_path = Path(f"{config_path}.backup")
                        import shutil
                        shutil.copy(config_path, backup_path)
                        
                        # 修正した設定を保存
                        with open(config_file, 'w', encoding='utf-8') as f:
                            json.dump(config_data, f, ensure_ascii=False, indent=2)
                        return {"success": True, "message": f"設定ファイルを自動修正: {config_path}"}
                
                return {"success": True, "message": f"設定ファイル検証OK: {config_path}"}
            except json.JSONDecodeError as e:
                # JSON解析エラーの場合、バックアップから復旧
                backup_path = Path(f"{config_path}.backup")
                if backup_path.exists():
                    import shutil
                    shutil.copy(backup_path, config_path)
                    return {"success": True, "message": f"設定ファイルをバックアップから復旧（JSONエラー）: {config_path}"}
                return {"error": f"設定ファイルJSON解析エラー: {e}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_resource_shortage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """リソース不足修復"""
        try:
            resource_type = context.get("resource_type", "memory")
            actions_taken = []
            
            if resource_type == "memory":
                # メモリ使用率を取得
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                
                if memory_percent > 85:
                    # ガベージコレクションを実行
                    import gc
                    gc.collect()
                    actions_taken.append("ガベージコレクション実行")
                    
                    # キャッシュをクリア
                    if self.auto_optimization:
                        try:
                            self.auto_optimization._clear_cache()
                            actions_taken.append("キャッシュクリア")
                        except:
                            pass
                    
                    # メモリ使用率が高いプロセスを終了（オプション）
                    if memory_percent > 95:
                        # メモリ使用率が高いプロセスを検索
                        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                            try:
                                if proc.info['memory_percent'] > 10:  # 10%以上使用
                                    proc_name = proc.info['name']
                                    # システムプロセスは除外
                                    if proc_name not in ['python.exe', 'pythonw.exe']:
                                        continue
                                    proc.terminate()
                                    actions_taken.append(f"プロセス終了: {proc_name}")
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                    
                    return {
                        "success": True,
                        "message": f"メモリ不足を解消（使用率: {memory_percent:.1f}%）",
                        "actions": actions_taken
                    }
            
            elif resource_type == "disk":
                # ディスク使用率を取得
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                
                if disk_percent > 85:
                    # 一時ファイルを削除
                    temp_dirs = [
                        Path("data/temp"),
                        Path("data/cache"),
                        Path("logs")
                    ]
                    
                    for temp_dir in temp_dirs:
                        if temp_dir.exists():
                            import shutil
                            try:
                                shutil.rmtree(temp_dir)
                                temp_dir.mkdir(parents=True, exist_ok=True)
                                actions_taken.append(f"一時ディレクトリクリア: {temp_dir}")
                            except:
                                pass
                    
                    # 古いログファイルを削除
                    log_dir = Path("logs")
                    if log_dir.exists():
                        import time
                        current_time = time.time()
                        for log_file in log_dir.glob("*.log"):
                            if current_time - log_file.stat().st_mtime > 7 * 24 * 3600:  # 7日以上古い
                                log_file.unlink()
                                actions_taken.append(f"古いログファイル削除: {log_file.name}")
                    
                    return {
                        "success": True,
                        "message": f"ディスク不足を解消（使用率: {disk_percent:.1f}%）",
                        "actions": actions_taken
                    }
            
            elif resource_type == "cpu":
                # CPU使用率を取得
                cpu_percent = psutil.cpu_percent(interval=1)
                
                if cpu_percent > 90:
                    # CPU使用率が高いプロセスを検索
                    processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                        try:
                            proc.cpu_percent()  # 最初の呼び出しは0を返す可能性がある
                            processes.append(proc)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    # CPU使用率を再取得
                    time.sleep(0.1)
                    for proc in processes:
                        try:
                            cpu = proc.cpu_percent()
                            if cpu > 50:  # 50%以上使用
                                proc_name = proc.info['name']
                                # システムプロセスは除外
                                if proc_name not in ['python.exe', 'pythonw.exe']:
                                    continue
                                # 優先度を下げる（Windows）
                                import os
                                if os.name == 'nt':
                                    import subprocess
                                    subprocess.run(['wmic', 'process', 'where', f'pid={proc.pid}', 'set', 'priority=below normal'])
                                    actions_taken.append(f"プロセス優先度を下げる: {proc_name}")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    return {
                        "success": True,
                        "message": f"CPU過負荷を軽減（使用率: {cpu_percent:.1f}%）",
                        "actions": actions_taken
                    }
            
            return {"error": f"不明なリソースタイプ: {resource_type}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_switch_network_path(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """ネットワークパス切り替え修復"""
        try:
            primary_url = context.get("primary_url")
            fallback_urls = context.get("fallback_urls", [])
            
            if not primary_url or not fallback_urls:
                return {"error": "primary_urlとfallback_urlsが必要です"}
            
            # プライマリURLをテスト
            try:
                import requests
                response = requests.get(f"{primary_url}/health", timeout=5)
                if response.status_code == 200:
                    return {"success": True, "message": f"プライマリURL接続OK: {primary_url}"}
            except:
                pass
            
            # フォールバックURLを試す
            for fallback_url in fallback_urls:
                try:
                    import requests
                    response = requests.get(f"{fallback_url}/health", timeout=5)
                    if response.status_code == 200:
                        return {
                            "success": True,
                            "message": f"フォールバックURLに切り替え: {fallback_url}",
                            "new_url": fallback_url
                        }
                except:
                    continue
            
            return {"error": "すべてのURL接続に失敗しました"}
        except Exception as e:
            return {"error": str(e)}
    
    def _repair_adjust_timeout(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """タイムアウト設定調整修復"""
        try:
            service_name = context.get("service_name")
            current_timeout = context.get("current_timeout", 30)
            timeout_config_path = context.get("timeout_config_path", "manaos_timeout_config.json")
            
            # タイムアウト設定を読み込み
            timeout_config_file = Path(timeout_config_path)
            if timeout_config_file.exists():
                import json
                with open(timeout_config_file, 'r', encoding='utf-8') as f:
                    timeout_config = json.load(f)
            else:
                timeout_config = {}
            
            # タイムアウトを増やす（現在の1.5倍、最大300秒）
            new_timeout = min(int(current_timeout * 1.5), 300)
            
            if service_name:
                timeout_config[service_name] = new_timeout
            else:
                timeout_config["default"] = new_timeout
            
            # 設定を保存
            timeout_config_file.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(timeout_config_file, 'w', encoding='utf-8') as f:
                json.dump(timeout_config, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "message": f"タイムアウト設定を調整: {current_timeout}s -> {new_timeout}s",
                "new_timeout": new_timeout
            }
        except Exception as e:
            return {"error": str(e)}
    
    def learn_error_pattern(self, error: Exception, context: Dict[str, Any]):
        """
        エラーパターンを学習
        
        Args:
            error: エラーオブジェクト
            context: エラー発生時のコンテキスト
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # エラーパターンのIDを生成
        pattern_id = f"{error_type}:{hash(error_message)}"
        
        if pattern_id in self.error_patterns:
            self.error_patterns[pattern_id].record_occurrence()
        else:
            self.error_patterns[pattern_id] = ErrorPattern(
                error_type,
                error_message,
                context
            )
        
        self._save_error_patterns()
        
        # 学習システムに記録
        if self.learning_system:
            try:
                self.learning_system.record_usage(
                    action="error_occurred",
                    context={
                        "error_type": error_type,
                        "error_message": error_message,
                        **context
                    },
                    result={"status": "error"}
                )
            except Exception as e:
                logger.warning(f"学習システム記録エラー: {e}")
    
    def select_repair_action(self, error_pattern: ErrorPattern) -> Optional[RepairAction]:
        """
        修復アクションを選択
        
        Args:
            error_pattern: エラーパターン
            
        Returns:
            選択された修復アクション
        """
        # 過去に成功した修復アクションを優先
        if error_pattern.successful_fixes:
            last_successful = error_pattern.successful_fixes[-1]
            action_name = last_successful["action"]
            for action in self.repair_actions:
                if action.name == action_name:
                    return action
        
        # 成功率が高いアクションを優先
        sorted_actions = sorted(
            self.repair_actions,
            key=lambda a: (a.get_success_rate(), a.priority),
            reverse=True
        )
        
        return sorted_actions[0] if sorted_actions else None
    
    def auto_repair(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        自動修復を実行
        
        Args:
            error: エラーオブジェクト
            context: エラー発生時のコンテキスト
            
        Returns:
            修復結果
        """
        if not self.config.get("enable_auto_repair", True):
            return {"skipped": True, "reason": "自動修復が無効です"}
        
        # エラーパターンを学習
        self.learn_error_pattern(error, context)
        
        # エラーパターンを取得
        error_type = type(error).__name__
        error_message = str(error)
        pattern_id = f"{error_type}:{hash(error_message)}"
        
        if pattern_id not in self.error_patterns:
            return {"error": "エラーパターンが見つかりません"}
        
        error_pattern = self.error_patterns[pattern_id]
        
        # 発生回数が閾値を超えている場合のみ修復を試みる
        if error_pattern.occurrence_count < self.config.get("repair_threshold", 3):
            return {"skipped": True, "reason": f"発生回数が閾値未満: {error_pattern.occurrence_count}"}
        
        # 修復アクションを選択
        repair_action = self.select_repair_action(error_pattern)
        if not repair_action:
            return {"error": "修復アクションが見つかりません"}
        
        # 修復アクションを実行
        repair_result = repair_action.execute(context)
        
        # 修復結果を記録
        error_pattern.record_fix_attempt(
            repair_action.name,
            repair_result.get("success", False)
        )
        
        self._save_error_patterns()
        
        # 修復履歴に記録
        repair_record = {
            "timestamp": datetime.now().isoformat(),
            "error_pattern": pattern_id,
            "repair_action": repair_action.name,
            "result": repair_result
        }
        self.repair_history.append(repair_record)
        
        # 修復成功時にコールバックを実行
        if repair_result.get("success") and self.on_repair_success:
            try:
                self.on_repair_success(repair_result)
            except Exception as e:
                logger.warning(f"修復成功コールバックエラー: {e}")
        
        return repair_result
    
    def auto_optimize(self) -> Dict[str, Any]:
        """
        自動最適化を実行
        
        Returns:
            最適化結果
        """
        if not self.config.get("enable_auto_optimization", True):
            return {"skipped": True, "reason": "自動最適化が無効です"}
        
        if not self.auto_optimization:
            return {"error": "Auto Optimizationが利用できません"}
        
        try:
            result = self.auto_optimization.optimize()
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    def auto_adapt(self, environment_changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        自動適応を実行
        
        Args:
            environment_changes: 環境変化の情報
            
        Returns:
            適応結果
        """
        if not self.config.get("enable_auto_adaptation", True):
            return {"skipped": True, "reason": "自動適応が無効です"}
        
        # 環境変化に応じた適応処理を実装
        adaptations = []
        
        # リソース変化への適応
        if "resource_usage" in environment_changes:
            resource_usage = environment_changes["resource_usage"]
            if resource_usage.get("memory_percent", 0) > 85:
                adaptations.append({
                    "type": "reduce_memory_usage",
                    "action": "clear_cache"
                })
        
        # ネットワーク変化への適応
        if "network_status" in environment_changes:
            network_status = environment_changes["network_status"]
            if not network_status.get("connected", True):
                adaptations.append({
                    "type": "reconnect_network",
                    "action": "reconnect_network"
                })
        
        return {
            "success": True,
            "adaptations": adaptations
        }
    
    def get_repair_statistics(self) -> Dict[str, Any]:
        """
        修復統計を取得
        
        Returns:
            修復統計の辞書
        """
        total_repairs = len(self.repair_history)
        successful_repairs = sum(1 for r in self.repair_history if r.get("result", {}).get("success", False))
        failed_repairs = total_repairs - successful_repairs
        
        # アクション別の成功率
        action_stats = {}
        for action in self.repair_actions:
            action_stats[action.name] = {
                "success_count": action.success_count,
                "failure_count": action.failure_count,
                "success_rate": action.get_success_rate(),
                "last_executed": action.last_executed
            }
        
        # エラーパターン別の修復成功率
        pattern_stats = {}
        for pattern_id, pattern in self.error_patterns.items():
            total_attempts = len(pattern.successful_fixes) + len(pattern.failed_fixes)
            if total_attempts > 0:
                success_rate = len(pattern.successful_fixes) / total_attempts
                pattern_stats[pattern_id] = {
                    "occurrence_count": pattern.occurrence_count,
                    "success_rate": success_rate,
                    "total_attempts": total_attempts
                }
        
        return {
            "total_repairs": total_repairs,
            "successful_repairs": successful_repairs,
            "failed_repairs": failed_repairs,
            "overall_success_rate": successful_repairs / total_repairs if total_repairs > 0 else 0.0,
            "action_statistics": action_stats,
            "pattern_statistics": pattern_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_repair_history(
        self,
        limit: int = 100,
        filter_success: Optional[bool] = None,
        filter_action: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        修復履歴を取得
        
        Args:
            limit: 取得件数
            filter_success: 成功/失敗でフィルタ（None=すべて）
            filter_action: アクション名でフィルタ（None=すべて）
        
        Returns:
            修復履歴のリスト
        """
        history = list(self.repair_history)
        
        # フィルタリング
        if filter_success is not None:
            history = [
                r for r in history
                if r.get("result", {}).get("success", False) == filter_success
            ]
        
        if filter_action:
            history = [
                r for r in history
                if r.get("repair_action") == filter_action
            ]
        
        # 最新順にソート
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return history[:limit]
    
    def analyze_repair_patterns(self) -> Dict[str, Any]:
        """
        修復パターンを分析
        
        Returns:
            分析結果の辞書
        """
        analysis = {
            "most_common_errors": [],
            "most_effective_actions": [],
            "least_effective_actions": [],
            "recommendations": []
        }
        
        # 最も頻繁に発生するエラー
        error_counts = {}
        for pattern_id, pattern in self.error_patterns.items():
            error_counts[pattern_id] = pattern.occurrence_count
        
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        analysis["most_common_errors"] = [
            {
                "pattern_id": pattern_id,
                "error_type": self.error_patterns[pattern_id].error_type,
                "occurrence_count": count
            }
            for pattern_id, count in sorted_errors[:10]
        ]
        
        # 最も効果的なアクション
        action_success_rates = [
            {
                "action": action.name,
                "success_rate": action.get_success_rate(),
                "total_executions": action.success_count + action.failure_count
            }
            for action in self.repair_actions
        ]
        sorted_actions = sorted(action_success_rates, key=lambda x: x["success_rate"], reverse=True)
        analysis["most_effective_actions"] = sorted_actions[:5]
        analysis["least_effective_actions"] = sorted_actions[-5:]
        
        # 推奨事項
        recommendations = []
        
        # 成功率が低いアクションの改善提案
        for action_info in analysis["least_effective_actions"]:
            if action_info["success_rate"] < 0.5 and action_info["total_executions"] > 5:
                recommendations.append({
                    "type": "action_improvement",
                    "action": action_info["action"],
                    "message": f"{action_info['action']}の成功率が低い（{action_info['success_rate']*100:.1f}%）ため、改善を検討してください"
                })
        
        # 頻繁に発生するエラーの対策提案
        for error_info in analysis["most_common_errors"][:5]:
            if error_info["occurrence_count"] > 10:
                recommendations.append({
                    "type": "preventive_measure",
                    "error_type": error_info["error_type"],
                    "message": f"{error_info['error_type']}が頻繁に発生しています（{error_info['occurrence_count']}回）。根本原因の調査を推奨します"
                })
        
        analysis["recommendations"] = recommendations
        
        return analysis
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        repair_stats = self.get_repair_statistics()
        repair_analysis = self.analyze_repair_patterns()
        
        status = {
            "error_patterns_count": len(self.error_patterns),
            "repair_actions_count": len(self.repair_actions),
            "repair_history_count": len(self.repair_history),
            "repair_statistics": repair_stats,
            "repair_analysis": repair_analysis,
            "learning_system_available": self.learning_system is not None,
            "auto_optimization_available": self.auto_optimization is not None,
            "predictive_maintenance_available": self.predictive_maintenance is not None,
            "autonomy_system_available": self.autonomy_system is not None,
            "self_evolution_available": self.self_evolution is not None,
            "self_protection_available": self.self_protection is not None,
            "self_management_available": self.self_management is not None,
            "config": self.config,
            "timestamp": datetime.now().isoformat()
        }
        
        # 各システムの状態を追加
        if self.self_evolution:
            try:
                status["self_evolution"] = self.self_evolution.get_status()
            except Exception as e:
                logger.warning(f"Self Evolution状態取得エラー: {e}")
        
        if self.self_protection:
            try:
                status["self_protection"] = self.self_protection.get_status()
            except Exception as e:
                logger.warning(f"Self Protection状態取得エラー: {e}")
        
        if self.self_management:
            try:
                status["self_management"] = self.self_management.get_status()
            except Exception as e:
                logger.warning(f"Self Management状態取得エラー: {e}")
        
        return status


def main():
    """テスト用メイン関数"""
    system = ComprehensiveSelfCapabilitiesSystem()
    
    # テスト: エラーパターンの学習
    try:
        raise ValueError("テストエラー")
    except Exception as e:
        system.learn_error_pattern(e, {"test": True})
    
    # テスト: 状態取得
    status = system.get_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

