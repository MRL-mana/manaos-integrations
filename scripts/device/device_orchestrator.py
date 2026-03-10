#!/usr/bin/env python3
"""
🎯 Device Orchestrator - デバイス統合管理システム
全デバイスを統合管理し、タスクを分散実行
"""

import json
import asyncio
import os
from manaos_logger import get_logger, get_service_logger
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import requests

try:
    from manaos_integrations._paths import ORCHESTRATOR_PORT, PIXEL7_BRIDGE_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import ORCHESTRATOR_PORT, PIXEL7_BRIDGE_PORT  # type: ignore
    except Exception:  # pragma: no cover
        ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "5106"))
        PIXEL7_BRIDGE_PORT = int(os.getenv("PIXEL7_BRIDGE_PORT", "5122"))

logger = get_service_logger("device-orchestrator")


class DeviceStatus(Enum):
    """デバイスステータス"""

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class Device:
    """デバイス情報"""

    device_id: str
    device_name: str
    device_type: str  # "manaos", "mothership", "x280", "konoha", "pixel7"
    api_endpoint: Optional[str]
    status: DeviceStatus
    capabilities: List[str]  # ["compute", "storage", "gpu", "camera"]
    current_load: float  # 0.0-1.0
    last_seen: str


@dataclass
class Task:
    """タスク"""

    task_id: str
    task_type: str  # "compute", "storage", "gpu", "camera"
    payload: Dict[str, Any]
    priority: int  # 1-10 (10が最高)
    assigned_device: Optional[str] = None
    status: str = "pending"  # "pending", "running", "completed", "failed"
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DeviceOrchestrator:
    """デバイス統合管理システム"""

    def __init__(self, config_path: str = "device_orchestrator_config.json"):
        """
        初期化

        Args:
            config_path: 設定ファイルのパス（相対の場合はこのスクリプトのディレクトリ基準）
        """
        self.config_path = Path(config_path)
        if not self.config_path.is_absolute():
            # MCP 等から別 cwd で呼ばれても workspace の設定を読む
            script_dir = Path(__file__).resolve().parent
            self.config_path = (script_dir / config_path).resolve()
        self.config = self._load_config()

        # デバイス管理
        self.devices: Dict[str, Device] = {}
        for device_config in self.config.get("devices", []):
            device = Device(
                device_id=device_config["device_id"],
                device_name=device_config["device_name"],
                device_type=device_config["device_type"],
                api_endpoint=device_config.get("api_endpoint"),
                status=DeviceStatus.OFFLINE,
                capabilities=device_config.get("capabilities", []),
                current_load=0.0,
                last_seen="",
            )
            self.devices[device.device_id] = device

        # タスクキュー
        self.task_queue: List[Task] = []
        self.running_tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []

        # リソースプール
        self.resource_pools = {"compute": [], "storage": [], "gpu": [], "camera": []}

        # 統計
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_devices": len(self.devices),
            "online_devices": 0,
        }

    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # デフォルト設定を作成
            default_config = {
                "devices": [
                    {
                        "device_id": "manaos",
                        "device_name": "ManaOS",
                        "device_type": "manaos",
                        "api_endpoint": f"http://127.0.0.1:{ORCHESTRATOR_PORT}",
                        "capabilities": ["compute", "storage"],
                    },
                    {
                        "device_id": "mothership",
                        "device_name": "Mothership",
                        "device_type": "mothership",
                        # 重要: 母艦はメインのWindows PC（このコードが実行されているPC）、GPU搭載
                        "api_endpoint": None,  # ローカル監視のみ
                        "capabilities": ["compute", "storage", "gpu"],
                    },
                    {
                        "device_id": "x280",
                        "device_name": "X280",
                        "device_type": "x280",
                        # 重要: X280は別のThinkPad Windows PC（母艦とは別のPC）
                        # Tailscale IP経由で接続: 100.127.121.20
                        "api_endpoint": "http://100.127.121.20:5120",
                        "capabilities": ["compute", "storage"],
                    },
                    {
                        "device_id": "konoha",
                        "device_name": "Konoha Server",
                        "device_type": "konoha",
                        "api_endpoint": "http://100.93.120.33:5106",
                        "capabilities": ["compute", "storage"],
                    },
                    {
                        "device_id": "pixel7",
                        "device_name": "Pixel 7",
                        "device_type": "pixel7",
                        "api_endpoint": os.getenv(
                            "PIXEL7_BRIDGE_URL",
                            f"http://127.0.0.1:{PIXEL7_BRIDGE_PORT}",
                        ),
                        "capabilities": ["camera", "storage"],
                    },
                ]
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config

    def discover_devices(self):
        """デバイスを自動検出"""
        logger.info("デバイスを検出中...")
        # 設定を再読み込みして最新の api_endpoint を反映
        self.config = self._load_config()
        self.devices.clear()
        for device_config in self.config.get("devices", []):
            device = Device(
                device_id=device_config["device_id"],
                device_name=device_config["device_name"],
                device_type=device_config["device_type"],
                api_endpoint=device_config.get("api_endpoint"),
                status=DeviceStatus.OFFLINE,
                capabilities=device_config.get("capabilities", []),
                current_load=0.0,
                last_seen="",
            )
            self.devices[device.device_id] = device

        for device_id, device in self.devices.items():
            if device.api_endpoint:
                # APIエンドポイント経由で確認
                try:
                    response = requests.get(f"{device.api_endpoint}/health", timeout=5)
                    if response.status_code == 200:
                        device.status = DeviceStatus.ONLINE
                        device.last_seen = datetime.now().isoformat()
                        # リソース情報を取得（オプション）
                        try:
                            health_data = response.json()
                            device.current_load = health_data.get("cpu_percent", 0.0) / 100.0
                        except (ValueError, KeyError) as e:
                            logger.debug("%s のヘルスデータ解析失敗: %s", device.device_name, e)
                    else:
                        device.status = DeviceStatus.OFFLINE
                except Exception as e:
                    logger.warning(f"{device.device_name}への接続エラー: {e}")
                    device.status = DeviceStatus.OFFLINE
            else:
                # ローカルデバイスの場合
                device.status = DeviceStatus.ONLINE
                device.last_seen = datetime.now().isoformat()

        # 統計を更新
        self.stats["online_devices"] = sum(
            1 for d in self.devices.values() if d.status == DeviceStatus.ONLINE
        )

        logger.info(
            f"デバイス検出完了: {self.stats['online_devices']}/{self.stats['total_devices']}オンライン"
        )

    def add_task(self, task_type: str, payload: Dict[str, Any], priority: int = 5) -> str:
        """
        タスクを追加

        Args:
            task_type: タスクタイプ
            payload: タスクペイロード
            priority: 優先度（1-10）

        Returns:
            タスクID
        """
        task_id = f"task_{int(time.time())}_{len(self.task_queue)}"
        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            created_at=datetime.now().isoformat(),
        )

        # 優先度順にソートして追加
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority, reverse=True)

        self.stats["total_tasks"] += 1
        logger.info(f"タスクを追加: {task_id} ({task_type}, priority={priority})")

        return task_id

    def _find_best_device(self, task_type: str) -> Optional[Device]:
        """最適なデバイスを検索"""
        available_devices = [
            d
            for d in self.devices.values()
            if d.status == DeviceStatus.ONLINE
            and task_type in d.capabilities
            and d.current_load < 0.9  # 90%未満の負荷
        ]

        if not available_devices:
            return None

        # 負荷が最も低いデバイスを選択
        best_device = min(available_devices, key=lambda d: d.current_load)
        return best_device

    def assign_task(self, task: Task) -> bool:
        """
        タスクをデバイスに割り当て

        Args:
            task: タスク

        Returns:
            成功時True
        """
        device = self._find_best_device(task.task_type)
        if not device:
            logger.warning(f"タスク {task.task_id} に割り当て可能なデバイスが見つかりません")
            return False

        task.assigned_device = device.device_id
        task.status = "running"
        task.started_at = datetime.now().isoformat()
        self.running_tasks[task.task_id] = task

        # デバイスの負荷を更新
        device.current_load += 0.1  # 簡易的な負荷増加

        logger.info(f"タスク {task.task_id} を {device.device_name} に割り当てました")
        return True

    def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        タスクを実行

        Args:
            task: タスク

        Returns:
            実行結果
        """
        device = self.devices.get(task.assigned_device)  # type: ignore
        if not device:
            return {"success": False, "error": f"デバイスが見つかりません: {task.assigned_device}"}

        if device.api_endpoint:
            # API経由で実行
            try:
                response = requests.post(
                    f"{device.api_endpoint}/api/execute", json=task.payload, timeout=300
                )
                if response.status_code == 200:
                    return {"success": True, "result": response.json()}
                else:
                    return {"success": False, "error": f"APIエラー: HTTP {response.status_code}"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            # ローカル実行（簡易実装）
            return {"success": True, "result": {"message": "Local execution not implemented"}}

    def process_task_queue(self):
        """タスクキューを処理"""
        while self.task_queue:
            task = self.task_queue[0]

            if self.assign_task(task):
                # タスクを実行
                result = self.execute_task(task)

                # タスクを完了
                self.task_queue.remove(task)
                task.completed_at = datetime.now().isoformat()

                if result["success"]:
                    task.status = "completed"
                    task.result = result.get("result")
                    self.stats["completed_tasks"] += 1
                else:
                    task.status = "failed"
                    task.error = result.get("error")
                    self.stats["failed_tasks"] += 1

                # デバイスの負荷を更新
                device = self.devices.get(task.assigned_device)  # type: ignore
                if device:
                    device.current_load = max(0.0, device.current_load - 0.1)

                self.completed_tasks.append(task)
                del self.running_tasks[task.task_id]
            else:
                # 割り当てできない場合は待機
                break

    def get_device_status(self) -> Dict[str, Any]:
        """デバイスステータスを取得"""
        return {
            "devices": [asdict(d) for d in self.devices.values()],
            "stats": self.stats,
            "queue_length": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
        }

    def get_status(self) -> Dict[str, Any]:
        """システム状態を取得（統一インターフェース）"""
        return self.get_device_status()

    def run(self):
        """オーケストレーターを実行"""
        logger.info("Device Orchestratorを開始します...")

        while True:
            try:
                # デバイスを検出
                self.discover_devices()

                # タスクキューを処理
                self.process_task_queue()

                # 待機
                time.sleep(10)
            except KeyboardInterrupt:
                logger.info("Device Orchestratorを停止します...")
                break
            except Exception as e:
                logger.error(f"オーケストレーターエラー: {e}")
                time.sleep(10)


def main():
    """メイン関数（テスト用）"""
    orchestrator = DeviceOrchestrator()

    # デバイスを検出
    orchestrator.discover_devices()

    # ステータスを表示
    status = orchestrator.get_device_status()
    print(json.dumps(status, indent=2, ensure_ascii=False, default=str))

    # テストタスクを追加
    task_id = orchestrator.add_task("compute", {"command": "echo test"}, priority=5)
    print(f"\nテストタスクを追加: {task_id}")

    # タスクキューを処理
    orchestrator.process_task_queue()


if __name__ == "__main__":
    main()
