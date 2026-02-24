#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧯 ManaOS 障害スナップショットシステム
サービス死亡時にメモリ使用量・直前ログ・実行中タスクを1ファイルに吐く
"""

import os
import json
import httpx
import psutil
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

from _paths import TASK_QUEUE_PORT

# ロガーの初期化
logger = get_service_logger("crash-snapshot")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("CrashSnapshot")

# タイムアウト設定の取得
timeout_config = get_timeout_config()


@dataclass
class CrashSnapshot:
    """障害スナップショット"""
    timestamp: str
    service_name: str
    service_port: int
    system_resources: Dict[str, Any]
    recent_logs: List[str]
    running_tasks: List[Dict[str, Any]]
    error_message: str
    stack_trace: Optional[str] = None


class CrashSnapshotManager:
    """障害スナップショット管理"""
    
    def __init__(self, snapshot_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            snapshot_dir: スナップショット保存ディレクトリ
        """
        self.snapshot_dir = snapshot_dir or Path(__file__).parent / "crash_snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✅ Crash Snapshot Manager初期化完了")
    
    def create_snapshot(
        self,
        service_name: str,
        service_port: int,
        error_message: str,
        stack_trace: Optional[str] = None
    ) -> Path:
        """
        障害スナップショットを作成
        
        Args:
            service_name: サービス名
            service_port: ポート番号
            error_message: エラーメッセージ
            stack_trace: スタックトレース（オプション）
        
        Returns:
            スナップショットファイルのパス
        """
        timestamp = datetime.now()
        snapshot_id = f"crash_{timestamp.strftime('%Y%m%d_%H%M%S')}_{service_name.replace(' ', '_')}"
        
        # システムリソース取得
        system_resources = self._get_system_resources()
        
        # 直前ログ取得
        recent_logs = self._get_recent_logs(service_name)
        
        # 実行中タスク取得
        running_tasks = self._get_running_tasks(service_port)
        
        # スナップショット作成
        snapshot = CrashSnapshot(
            timestamp=timestamp.isoformat(),
            service_name=service_name,
            service_port=service_port,
            system_resources=system_resources,
            recent_logs=recent_logs,
            running_tasks=running_tasks,
            error_message=error_message,
            stack_trace=stack_trace
        )
        
        # ファイルに保存
        snapshot_file = self.snapshot_dir / f"{snapshot_id}.json"
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(snapshot), f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 障害スナップショット作成: {snapshot_file}")
        
        # 人間が読みやすい形式でも保存
        readable_file = self.snapshot_dir / f"{snapshot_id}.txt"
        self._save_readable_snapshot(snapshot, readable_file)
        
        return snapshot_file
    
    def _get_system_resources(self) -> Dict[str, Any]:
        """システムリソース情報を取得"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # プロセス情報
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['name'] and 'python' in proc_info['name'].lower():
                        processes.append({
                            "pid": proc_info['pid'],
                            "name": proc_info['name'],
                            "memory_mb": round(proc_info['memory_info'].rss / (1024**2), 2),
                            "cpu_percent": proc_info['cpu_percent'] or 0.0
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": disk.percent
                },
                "python_processes": processes[:20]  # 最新20件
            }
        except Exception as e:
            logger.error(f"システムリソース取得エラー: {e}")
            return {"error": str(e)}
    
    def _get_recent_logs(self, service_name: str, lines: int = 50) -> List[str]:
        """直前ログを取得"""
        logs = []
        
        try:
            log_dir = Path(__file__).parent / "logs"
            script_name = service_name.lower().replace(" ", "_")
            
            # エラーログを優先
            error_log_file = log_dir / f"{script_name}_error.log"
            if error_log_file.exists():
                with open(error_log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    log_lines = f.readlines()
                    logs.extend(log_lines[-lines:])
            
            # 通常ログ
            log_file = log_dir / f"{script_name}.log"
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    log_lines = f.readlines()
                    logs.extend(log_lines[-lines:])
        except Exception as e:
            logger.error(f"ログ取得エラー: {e}")
            logs.append(f"ログ取得エラー: {e}")
        
        return logs[:lines * 2]  # 最大100行
    
    def _get_running_tasks(self, service_port: int) -> List[Dict[str, Any]]:
        """実行中タスクを取得"""
        tasks = []
        
        try:
            # Task Queueから実行中タスクを取得
            response = httpx.get(
                f"http://127.0.0.1:{TASK_QUEUE_PORT}/api/status",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                # 実行中タスクの詳細を取得（実装が必要）
                tasks.append({
                    "source": "task_queue",
                    "status": data.get("status", "unknown"),
                    "pending_tasks": data.get("pending_tasks", 0)
                })
        except Exception as e:
            logger.debug(f"実行中タスク取得エラー: {e}")
            tasks.append({
                "source": "error",
                "error": str(e)
            })
        
        return tasks
    
    def _save_readable_snapshot(self, snapshot: CrashSnapshot, file_path: Path):
        """人間が読みやすい形式で保存"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ManaOS 障害スナップショット\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"タイムスタンプ: {snapshot.timestamp}\n")
            f.write(f"サービス名: {snapshot.service_name}\n")
            f.write(f"ポート: {snapshot.service_port}\n")
            f.write(f"\n")
            
            f.write("=" * 80 + "\n")
            f.write("エラーメッセージ\n")
            f.write("=" * 80 + "\n")
            f.write(f"{snapshot.error_message}\n\n")
            
            if snapshot.stack_trace:
                f.write("=" * 80 + "\n")
                f.write("スタックトレース\n")
                f.write("=" * 80 + "\n")
                f.write(f"{snapshot.stack_trace}\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("システムリソース\n")
            f.write("=" * 80 + "\n")
            f.write(json.dumps(snapshot.system_resources, indent=2, ensure_ascii=False) + "\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("直前ログ（最新50行）\n")
            f.write("=" * 80 + "\n")
            for log_line in snapshot.recent_logs[-50:]:
                f.write(log_line)
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("実行中タスク\n")
            f.write("=" * 80 + "\n")
            f.write(json.dumps(snapshot.running_tasks, indent=2, ensure_ascii=False) + "\n")
    
    def get_recent_snapshots(self, limit: int = 10) -> List[Path]:
        """最近のスナップショットを取得"""
        snapshots = sorted(
            self.snapshot_dir.glob("crash_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return snapshots[:limit]


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

snapshot_manager = CrashSnapshotManager()

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Crash Snapshot"})

@app.route('/api/snapshot', methods=['POST'])
def create_snapshot_endpoint():
    """スナップショット作成エンドポイント"""
    data = request.get_json() or {}
    
    service_name = data.get("service_name", "Unknown")
    service_port = data.get("service_port", 0)
    error_message = data.get("error_message", "Unknown error")
    stack_trace = data.get("stack_trace")
    
    snapshot_file = snapshot_manager.create_snapshot(
        service_name=service_name,
        service_port=service_port,
        error_message=error_message,
        stack_trace=stack_trace
    )
    
    return jsonify({
        "status": "success",
        "snapshot_file": str(snapshot_file),
        "message": "スナップショットを作成しました"
    })

@app.route('/api/snapshots', methods=['GET'])
def get_snapshots_endpoint():
    """スナップショット一覧取得"""
    limit = request.args.get("limit", 10, type=int)
    snapshots = snapshot_manager.get_recent_snapshots(limit)
    
    snapshot_info = []
    for snapshot_file in snapshots:
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                snapshot_info.append({
                    "file": snapshot_file.name,
                    "timestamp": data.get("timestamp"),
                    "service_name": data.get("service_name"),
                    "error_message": data.get("error_message", "")[:100]
                })
        except Exception as e:
            snapshot_info.append({
                "file": snapshot_file.name,
                "error": str(e)
            })
    
    return jsonify({
        "snapshots": snapshot_info,
        "count": len(snapshot_info)
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5113))
    logger.info(f"🧯 Crash Snapshot System起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

