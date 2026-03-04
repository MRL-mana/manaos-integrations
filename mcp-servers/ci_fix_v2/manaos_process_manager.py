#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 ManaOS プロセス管理モジュール (SSOT)
Windows環境でのプロセス管理を提供する **唯一の** モジュール。

各サービスやスクリプトはこのモジュールの ProcessManager クラスまたは
ショートカット関数を使用してプロセスの起動・停止・監視を行う。

パターン対応:
  - psutil.Process(pid) による Graceful terminate → wait → kill
  - psutil.process_iter によるキーワード / スクリプト名マッチ終了
  - ポート指定 (psutil.net_connections) によるプロセス特定・終了
  - PID 指定による直接終了
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import psutil

try:
    from unified_logging import get_service_logger
    logger = get_service_logger("manaos-process-manager")
except ImportError:
    try:
        from unified_logging import get_service_logger
        logger = get_service_logger("manaos-process-manager")
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

try:
    from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
except ImportError:
    ManaOSErrorHandler = None  # type: ignore[misc,assignment]

# プロセス情報ファイル
PROCESS_INFO_FILE = Path(__file__).parent / "process_info.json"


class ProcessManager:
    """プロセス管理クラス"""
    
    def __init__(self, service_name: str):
        """
        初期化
        
        Args:
            service_name: サービス名
        """
        self.service_name = service_name
        self.error_handler = ManaOSErrorHandler(service_name) if ManaOSErrorHandler else None
        self.process_info_file = PROCESS_INFO_FILE
    
    def get_process_info(self, script_name: str) -> Optional[Dict[str, Any]]:
        """
        プロセス情報を取得
        
        Args:
            script_name: スクリプト名
        
        Returns:
            プロセス情報（見つからない場合はNone）
        """
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent', 'create_time']):
                try:
                    if proc.info['cmdline'] and script_name in ' '.join(proc.info['cmdline']):
                        return {
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "memory_mb": round(proc.info['memory_info'].rss / (1024**2), 2),
                            "cpu_percent": proc.info['cpu_percent'] or 0.0,
                            "create_time": datetime.fromtimestamp(proc.info['create_time']).isoformat()
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return None
        except Exception as e:
            logger.error(f"プロセス情報取得エラー: {e}")
            return None
    
    def save_process_info(self, script_name: str, pid: int):
        """
        プロセス情報を保存
        
        Args:
            script_name: スクリプト名
            pid: プロセスID
        """
        try:
            # 既存の情報を読み込み
            process_info = {}
            if self.process_info_file.exists():
                with open(self.process_info_file, 'r', encoding='utf-8') as f:
                    process_info = json.load(f)
            
            # プロセス情報を更新
            process_info[script_name] = {
                "pid": pid,
                "service_name": self.service_name,
                "started_at": datetime.now().isoformat()
            }
            
            # 保存
            with open(self.process_info_file, 'w', encoding='utf-8') as f:
                json.dump(process_info, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"プロセス情報を保存: {script_name} (PID: {pid})")
        except Exception as e:
            logger.error(f"プロセス情報保存エラー: {e}")
    
    def cleanup_process(self, script_name: str) -> bool:
        """
        プロセスをクリーンアップ
        
        Args:
            script_name: スクリプト名
        
        Returns:
            成功か
        """
        try:
            # プロセス情報を読み込み
            if not self.process_info_file.exists():
                return True
            
            with open(self.process_info_file, 'r', encoding='utf-8') as f:
                process_info = json.load(f)
            
            if script_name not in process_info:
                return True
            
            pid = process_info[script_name].get("pid")
            if pid:
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    proc.wait(timeout=5)
                    logger.info(f"プロセスを終了: {script_name} (PID: {pid})")
                except psutil.NoSuchProcess:
                    logger.debug(f"プロセスは既に終了しています: {script_name} (PID: {pid})")
                except psutil.TimeoutExpired:
                    proc.kill()
                    logger.warning(f"プロセスを強制終了: {script_name} (PID: {pid})")
            
            # プロセス情報から削除
            del process_info[script_name]
            with open(self.process_info_file, 'w', encoding='utf-8') as f:
                json.dump(process_info, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"プロセスクリーンアップエラー: {e}")
            return False
    
    def cleanup_all_processes(self) -> int:
        """
        全プロセスをクリーンアップ
        
        Returns:
            クリーンアップしたプロセス数
        """
        try:
            if not self.process_info_file.exists():
                return 0
            
            with open(self.process_info_file, 'r', encoding='utf-8') as f:
                process_info = json.load(f)
            
            cleaned_count = 0
            for script_name in list(process_info.keys()):
                if self.cleanup_process(script_name):
                    cleaned_count += 1
            
            return cleaned_count
        except Exception as e:
            logger.error(f"全プロセスクリーンアップエラー: {e}")
            return 0
    
    def get_all_processes(self) -> Dict[str, Dict[str, Any]]:
        """
        全プロセス情報を取得
        
        Returns:
            プロセス情報辞書
        """
        try:
            if not self.process_info_file.exists():
                return {}
            
            with open(self.process_info_file, 'r', encoding='utf-8') as f:
                process_info = json.load(f)
            
            # 各プロセスの現在の状態を取得
            result = {}
            for script_name, info in process_info.items():
                pid = info.get("pid")
                if pid:
                    try:
                        proc = psutil.Process(pid)
                        result[script_name] = {
                            **info,
                            "status": "running",
                            "memory_mb": round(proc.memory_info().rss / (1024**2), 2),
                            "cpu_percent": proc.cpu_percent()
                        }
                    except psutil.NoSuchProcess:
                        result[script_name] = {
                            **info,
                            "status": "stopped"
                        }
                else:
                    result[script_name] = {
                        **info,
                        "status": "unknown"
                    }
            
            return result
        except Exception as e:
            logger.error(f"全プロセス情報取得エラー: {e}")
            return {}
    
    def check_port_in_use(self, port: int) -> bool:
        """
        ポートが使用中かチェック
        
        Args:
            port: ポート番号
        
        Returns:
            使用中ならTrue
        """
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    return True
            return False
        except Exception as e:
            logger.error(f"ポートチェックエラー: {e}")
            return False
    
    def get_processes_by_port(self, port: int) -> List[Dict[str, Any]]:
        """
        指定ポートを使用しているプロセスを取得
        
        Args:
            port: ポート番号
        
        Returns:
            プロセス情報のリスト
        """
        try:
            processes = []
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    try:
                        proc = psutil.Process(conn.pid)
                        processes.append({
                            "pid": conn.pid,
                            "name": proc.name(),
                            "cmdline": ' '.join(proc.cmdline()) if proc.cmdline() else "",
                            "memory_mb": round(proc.memory_info().rss / (1024**2), 2),
                            "cpu_percent": proc.cpu_percent(),
                            "create_time": datetime.fromtimestamp(proc.create_time()).isoformat()
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            return processes
        except Exception as e:
            logger.error(f"ポートプロセス取得エラー: {e}")
            return []
    
    def kill_processes_by_port(self, port: int, script_name: str = None) -> int:
        """
        指定ポートを使用しているプロセスを終了
        
        Args:
            port: ポート番号
            script_name: スクリプト名（指定時は該当スクリプトのみ終了）
        
        Returns:
            終了したプロセス数
        """
        try:
            processes = self.get_processes_by_port(port)
            killed_count = 0
            
            for proc_info in processes:
                pid = proc_info["pid"]
                cmdline = proc_info.get("cmdline", "")
                
                # script_nameが指定されている場合、該当スクリプトのみ終了
                if script_name and script_name not in cmdline:
                    continue
                
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    proc.wait(timeout=5)
                    logger.info(f"プロセスを終了: PID {pid} (Port: {port})")
                    killed_count += 1
                except psutil.NoSuchProcess:
                    logger.debug(f"プロセスは既に終了しています: PID {pid}")
                except psutil.TimeoutExpired:
                    proc.kill()
                    logger.warning(f"プロセスを強制終了: PID {pid} (Port: {port})")
                    killed_count += 1
                except Exception as e:
                    logger.error(f"プロセス終了エラー (PID {pid}): {e}")
            
            return killed_count
        except Exception as e:
            logger.error(f"ポートプロセス終了エラー: {e}")
            return 0
    
    def kill_processes_by_script(self, script_name: str) -> int:
        """
        指定スクリプトを実行している全プロセスを終了
        
        Args:
            script_name: スクリプト名
        
        Returns:
            終了したプロセス数
        """
        try:
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['cmdline'] and script_name in ' '.join(proc.info['cmdline']):
                        pid = proc.info['pid']
                        proc_obj = psutil.Process(pid)
                        proc_obj.terminate()
                        proc_obj.wait(timeout=5)
                        logger.info(f"プロセスを終了: {script_name} (PID: {pid})")
                        killed_count += 1
                except psutil.NoSuchProcess:
                    continue
                except psutil.TimeoutExpired:
                    proc_obj.kill()
                    logger.warning(f"プロセスを強制終了: {script_name} (PID: {pid})")
                    killed_count += 1
                except (psutil.AccessDenied, Exception) as e:
                    logger.debug(f"プロセス終了スキップ (PID {proc.info.get('pid')}): {e}")
                    continue
            
            return killed_count
        except Exception as e:
            logger.error(f"スクリプトプロセス終了エラー: {e}")
            return 0

    # ── 追加メソッド: 全パターン対応 ──────────────────

    def kill_by_pid(self, pid: int, graceful_timeout: int = 5) -> bool:
        """PID指定でプロセスを終了 (terminate → wait → kill).

        Args:
            pid: プロセスID
            graceful_timeout: terminate 後の待機秒数

        Returns:
            終了に成功したか
        """
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            proc.wait(timeout=graceful_timeout)
            logger.info(f"プロセスを終了: {name} (PID: {pid})")
            return True
        except psutil.NoSuchProcess:
            logger.debug(f"プロセスは既に終了しています: PID {pid}")
            return True
        except psutil.TimeoutExpired:
            try:
                psutil.Process(pid).kill()
                logger.warning(f"プロセスを強制終了: PID {pid}")
                return True
            except psutil.NoSuchProcess:
                return True
        except psutil.AccessDenied:
            logger.warning(f"アクセス拒否: PID {pid} — taskkill にフォールバック")
            return self._taskkill_pid(pid)
        except Exception as e:
            logger.error(f"PID {pid} 終了エラー: {e}")
            return False

    def kill_processes_by_keywords(
        self,
        keywords: List[str],
        exclude_pids: Optional[List[int]] = None,
    ) -> int:
        """コマンドラインにキーワードを含むプロセスを終了.

        Args:
            keywords: どれか一つを含めば対象とする文字列リスト
            exclude_pids: 終了対象から除外する PID

        Returns:
            終了したプロセス数
        """
        exclude = set(exclude_pids or [])
        exclude.add(os.getpid())  # 自分自身は除外
        killed = 0
        seen: set[int] = set()

        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                pid = proc.info["pid"]
                if pid in exclude or pid in seen:
                    continue
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                if not cmdline:
                    continue
                for kw in keywords:
                    if kw.lower() in cmdline:
                        if self.kill_by_pid(pid):
                            killed += 1
                        seen.add(pid)
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return killed

    def list_top_processes(
        self,
        sort_by: str = "cpu",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """CPU / メモリ上位プロセスを返す.

        Args:
            sort_by: ``"cpu"`` or ``"memory"``
            limit: 返す件数
        """
        procs: list[dict] = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = p.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_mb": round((info["memory_info"].rss if info["memory_info"] else 0) / (1024 ** 2), 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        key = "cpu_percent" if sort_by == "cpu" else "memory_mb"
        procs.sort(key=lambda x: x[key], reverse=True)
        return procs[:limit]

    # ── 低レベルフォールバック ────────────────────────

    @staticmethod
    def _taskkill_pid(pid: int) -> bool:
        """taskkill /F /PID で強制終了 (psutil AccessDenied のフォールバック)."""
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                timeout=10,
            )
            return True
        except Exception as e:
            logger.error(f"taskkill 失敗 (PID {pid}): {e}")
            return False


# グローバルインスタンス
_process_manager: Optional[ProcessManager] = None


def get_process_manager(service_name: str = "ProcessManager") -> ProcessManager:
    """
    プロセス管理インスタンスを取得
    
    Args:
        service_name: サービス名
    
    Returns:
        ProcessManagerインスタンス
    """
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager(service_name)
    return _process_manager

