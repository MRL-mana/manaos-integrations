#!/usr/bin/env python3
"""
🖥️ Windows Automation Toolkit - 母艦PC自動化ツールキット
システム情報取得、スクリーンショット、プロセス管理、GPU/CPU監視、ウィンドウ操作、ソフトウェア管理
"""

import os
import subprocess
import json
import time
from manaos_logger import get_logger
from manaos_process_manager import get_process_manager
import ctypes
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

try:
    import psutil
except ImportError:
    psutil = None

try:
    import mss
    import mss.tools
except ImportError:
    mss = None

logger = get_service_logger("windows-automation-toolkit")
# ─── データクラス ───────────────────────────────────────

@dataclass
class SystemInfo:
    """システム情報"""
    hostname: str
    os_name: str
    os_version: str
    os_build: str
    cpu_name: str
    cpu_cores_physical: int
    cpu_cores_logical: int
    ram_total_gb: float
    gpu_name: str
    uptime_hours: float


@dataclass
class ResourceUsage:
    """リソース使用状況"""
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    ram_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    gpu_usage_percent: Optional[float]
    gpu_memory_used_mb: Optional[float]
    gpu_memory_total_mb: Optional[float]
    gpu_temp_celsius: Optional[float]
    network_sent_mb: float
    network_recv_mb: float
    timestamp: str


@dataclass
class ProcessInfo:
    """プロセス情報"""
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    status: str
    create_time: str


@dataclass
class WindowInfo:
    """ウィンドウ情報"""
    hwnd: int
    title: str
    class_name: str
    visible: bool
    rect: Dict[str, int]  # left, top, right, bottom


@dataclass
class ResourceAlert:
    """リソースアラート"""
    metric: str  # "cpu", "ram", "disk", "gpu_temp", "gpu_memory"
    value: float
    threshold: float
    alert_type: str  # "warning", "critical"
    timestamp: str


# ─── メインクラス ───────────────────────────────────────

class WindowsAutomationToolkit:
    """Windows母艦PC自動化ツールキット"""

    def __init__(self, config_path: str = "windows_automation_config.json"):
        """
        初期化

        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.screenshot_dir = Path(self.config.get("screenshot_dir", "./screenshots/windows"))
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # リソース監視閾値
        self.alerts = {
            "cpu_warning": self.config.get("cpu_warning_threshold", 80),
            "cpu_critical": self.config.get("cpu_critical_threshold", 95),
            "ram_warning": self.config.get("ram_warning_threshold", 80),
            "ram_critical": self.config.get("ram_critical_threshold", 95),
            "disk_warning": self.config.get("disk_warning_threshold", 85),
            "disk_critical": self.config.get("disk_critical_threshold", 95),
            "gpu_temp_warning": self.config.get("gpu_temp_warning", 80),
            "gpu_temp_critical": self.config.get("gpu_temp_critical", 90),
            "monitor_interval": self.config.get("monitor_interval", 60),
        }

        if not psutil:
            logger.error("psutil がインストールされていません: pip install psutil")
        if not mss:
            logger.warning("mss がインストールされていません: pip install mss")

    # ─── Config ─────────────────────────────────────

    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        default_config = {
            "screenshot_dir": "./screenshots/windows",
            "cpu_warning_threshold": 80,
            "cpu_critical_threshold": 95,
            "ram_warning_threshold": 80,
            "ram_critical_threshold": 95,
            "disk_warning_threshold": 85,
            "disk_critical_threshold": 95,
            "gpu_temp_warning": 80,
            "gpu_temp_critical": 90,
            "monitor_interval": 60,
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config

    # ─── システム情報 ───────────────────────────────

    def get_system_info(self) -> Dict[str, Any]:
        """
        システム情報を一括取得

        Returns:
            SystemInfo の辞書表現
        """
        try:
            cpu_name = platform.processor() or "Unknown"
            # WMICでCPU名を取得（より正確）
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-CimInstance Win32_Processor).Name"],
                    capture_output=True, text=True, timeout=10
                )
                if r.returncode == 0 and r.stdout.strip():
                    cpu_name = r.stdout.strip()
            except Exception:
                pass

            gpu_name = self._get_gpu_name()
            boot_time = datetime.fromtimestamp(psutil.boot_time()) if psutil else None
            uptime_hours = (datetime.now() - boot_time).total_seconds() / 3600 if boot_time else 0

            info = SystemInfo(
                hostname=platform.node(),
                os_name=platform.system(),
                os_version=platform.version(),
                os_build=platform.platform(),
                cpu_name=cpu_name,
                cpu_cores_physical=psutil.cpu_count(logical=False) if psutil else 0,
                cpu_cores_logical=psutil.cpu_count(logical=True) if psutil else 0,
                ram_total_gb=round(psutil.virtual_memory().total / (1024**3), 1) if psutil else 0,
                gpu_name=gpu_name,
                uptime_hours=round(uptime_hours, 1),
            )
            return asdict(info)
        except Exception as e:
            logger.error(f"システム情報取得エラー: {e}")
            return {"error": str(e)}

    def _get_gpu_name(self) -> str:
        """GPU名を取得"""
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip().split('\n')[0]
        except FileNotFoundError:
            pass
        except Exception:
            pass

        # フォールバック: WMI
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_VideoController).Name"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return r.stdout.strip().split('\n')[0]
        except Exception:
            pass
        return "Unknown"

    # ─── リソース使用量 ─────────────────────────────

    def get_resource_usage(self) -> Dict[str, Any]:
        """
        CPU/RAM/Disk/GPU/ネットワークの現在の使用状況

        Returns:
            ResourceUsage の辞書表現
        """
        if not psutil:
            return {"error": "psutil が必要です"}

        try:
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage('C:\\')
            net = psutil.net_io_counters()
            gpu = self._get_gpu_stats()

            usage = ResourceUsage(
                cpu_percent=psutil.cpu_percent(interval=1),
                ram_used_gb=round(vm.used / (1024**3), 2),
                ram_total_gb=round(vm.total / (1024**3), 2),
                ram_percent=vm.percent,
                disk_used_gb=round(disk.used / (1024**3), 1),
                disk_total_gb=round(disk.total / (1024**3), 1),
                disk_percent=round(disk.percent, 1),
                gpu_usage_percent=gpu.get("utilization"),
                gpu_memory_used_mb=gpu.get("memory_used"),
                gpu_memory_total_mb=gpu.get("memory_total"),
                gpu_temp_celsius=gpu.get("temperature"),
                network_sent_mb=round(net.bytes_sent / (1024**2), 1),
                network_recv_mb=round(net.bytes_recv / (1024**2), 1),
                timestamp=datetime.now().isoformat(),
            )
            return asdict(usage)
        except Exception as e:
            logger.error(f"リソース使用量取得エラー: {e}")
            return {"error": str(e)}

    def _get_gpu_stats(self) -> Dict[str, Any]:
        """nvidia-smi からGPU統計を取得"""
        try:
            r = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = [p.strip() for p in r.stdout.strip().split('\n')[0].split(',')]
                return {
                    "utilization": float(parts[0]),
                    "memory_used": float(parts[1]),
                    "memory_total": float(parts[2]),
                    "temperature": float(parts[3]),
                }
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"GPU統計取得エラー: {e}")
        return {}

    def check_resource_alerts(self) -> List[Dict[str, Any]]:
        """
        リソース使用量を閾値と比較し、アラートを返す

        Returns:
            ResourceAlert のリスト
        """
        usage = self.get_resource_usage()
        if "error" in usage:
            return [{"error": usage["error"]}]

        alerts = []
        now = datetime.now().isoformat()

        def _check(metric: str, value: Optional[float], warn_key: str, crit_key: str):
            if value is None:
                return
            crit = self.alerts.get(crit_key, 95)
            warn = self.alerts.get(warn_key, 80)
            if value >= crit:
                alerts.append(asdict(ResourceAlert(metric, value, crit, "critical", now)))
            elif value >= warn:
                alerts.append(asdict(ResourceAlert(metric, value, warn, "warning", now)))

        _check("cpu", usage["cpu_percent"], "cpu_warning", "cpu_critical")
        _check("ram", usage["ram_percent"], "ram_warning", "ram_critical")
        _check("disk", usage["disk_percent"], "disk_warning", "disk_critical")
        _check("gpu_temp", usage.get("gpu_temp_celsius"), "gpu_temp_warning", "gpu_temp_critical")

        return alerts

    # ─── スクリーンショット ─────────────────────────

    def take_screenshot(self, filename: Optional[str] = None, monitor: int = 0) -> Dict[str, Any]:
        """
        スクリーンショットを取得

        Args:
            filename: ファイル名（省略時は自動生成）
            monitor: モニター番号（0=全画面, 1=メイン, 2=2番目...）

        Returns:
            {"success": bool, "path": str, "size_kb": float}
        """
        if not mss:
            return {"success": False, "error": "mss がインストールされていません"}

        try:
            if not filename:
                filename = f"win_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            filepath = self.screenshot_dir / filename

            with mss.mss() as sct:
                if monitor == 0:
                    # 全モニターを合成
                    shot = sct.grab(sct.monitors[0])
                else:
                    monitors = sct.monitors
                    if monitor >= len(monitors):
                        return {"success": False, "error": f"モニター{monitor}が存在しません（最大{len(monitors)-1}）"}
                    shot = sct.grab(monitors[monitor])

                mss.tools.to_png(shot.rgb, shot.size, output=str(filepath))

            size_kb = filepath.stat().st_size / 1024
            logger.info(f"スクリーンショット保存: {filepath} ({size_kb:.1f}KB)")
            return {"success": True, "path": str(filepath), "size_kb": round(size_kb, 1)}
        except Exception as e:
            logger.error(f"スクリーンショットエラー: {e}")
            return {"success": False, "error": str(e)}

    def get_monitor_info(self) -> List[Dict[str, Any]]:
        """接続されているモニター情報を取得"""
        if not mss:
            return [{"error": "mss がインストールされていません"}]

        try:
            with mss.mss() as sct:
                result = []
                for i, mon in enumerate(sct.monitors):
                    result.append({
                        "monitor": i,
                        "label": "全画面合成" if i == 0 else f"モニター{i}",
                        "left": mon["left"],
                        "top": mon["top"],
                        "width": mon["width"],
                        "height": mon["height"],
                    })
                return result
        except Exception as e:
            return [{"error": str(e)}]

    # ─── プロセス管理 ───────────────────────────────

    def get_top_processes(self, sort_by: str = "cpu", limit: int = 10) -> List[Dict[str, Any]]:
        """
        CPU/メモリ使用量トップのプロセスを取得

        Args:
            sort_by: "cpu" または "memory"
            limit: 取得件数

        Returns:
            ProcessInfo のリスト
        """
        if not psutil:
            return [{"error": "psutil が必要です"}]

        try:
            pm = get_process_manager()
            return pm.list_top_processes(sort_by=sort_by, limit=limit)
        except Exception as e:
            logger.error(f"プロセス取得エラー: {e}")
            return [{"error": str(e)}]

    def kill_process(self, pid: int) -> Dict[str, Any]:
        """
        プロセスを終了

        Args:
            pid: プロセスID

        Returns:
            {"success": bool, "name": str}
        """
        if not psutil:
            return {"success": False, "error": "psutil が必要です"}

        try:
            # 存在確認 (NoSuchProcess / AccessDenied を先にキャッチ)
            proc = psutil.Process(pid)
            name = proc.name()
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"PID {pid} が見つかりません"}
        except psutil.AccessDenied:
            return {"success": False, "error": f"PID {pid} のアクセスが拒否されました（管理者権限が必要）"}

        try:
            pm = get_process_manager()
            success = pm.kill_by_pid(pid)
            if success:
                logger.info(f"プロセス終了: {name} (PID {pid})")
                return {"success": True, "name": name, "pid": pid}
            return {"success": False, "error": f"PID {pid} の終了に失敗"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_application(self, command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        アプリケーションを起動

        Args:
            command: 実行ファイル名またはパス
            args: 引数リスト

        Returns:
            {"success": bool, "pid": int}
        """
        try:
            cmd = [command] + (args or [])
            proc = subprocess.Popen(cmd, shell=False)
            logger.info(f"アプリ起動: {command} (PID {proc.pid})")
            return {"success": True, "pid": proc.pid, "command": command}
        except FileNotFoundError:
            return {"success": False, "error": f"{command} が見つかりません"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── ウィンドウ管理 ─────────────────────────────

    def list_windows(self) -> List[Dict[str, Any]]:
        """
        表示中のウィンドウ一覧を取得

        Returns:
            WindowInfo のリスト
        """
        import ctypes.wintypes as wintypes

        windows = []
        try:
            user32 = ctypes.windll.user32

            def _enum_callback(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        title = buf.value

                        # クラス名
                        class_buf = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(hwnd, class_buf, 256)

                        # ウィンドウ位置
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))

                        windows.append(asdict(WindowInfo(
                            hwnd=hwnd,
                            title=title,
                            class_name=class_buf.value,
                            visible=True,
                            rect={
                                "left": rect.left, "top": rect.top,
                                "right": rect.right, "bottom": rect.bottom
                            }
                        )))
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
            user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)

        except Exception as e:
            logger.error(f"ウィンドウ一覧取得エラー: {e}")
            return [{"error": str(e)}]

        return windows

    def focus_window(self, hwnd: Optional[int] = None, title_contains: Optional[str] = None) -> Dict[str, Any]:
        """
        ウィンドウを前面に表示

        Args:
            hwnd: ウィンドウハンドル（直接指定）
            title_contains: タイトルに含まれる文字列（部分一致検索）

        Returns:
            {"success": bool, "title": str}
        """
        try:
            user32 = ctypes.windll.user32

            if title_contains and not hwnd:
                for win in self.list_windows():
                    if title_contains.lower() in win.get("title", "").lower():
                        hwnd = win["hwnd"]
                        break
                if not hwnd:
                    return {"success": False, "error": f"'{title_contains}' を含むウィンドウが見つかりません"}

            if not hwnd:
                return {"success": False, "error": "hwnd または title_contains を指定してください"}

            # SW_RESTORE = 9
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)

            # タイトル取得
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)

            return {"success": True, "hwnd": hwnd, "title": buf.value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def minimize_window(self, hwnd: int) -> Dict[str, Any]:
        """ウィンドウを最小化"""
        try:
            ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            return {"success": True, "hwnd": hwnd}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def maximize_window(self, hwnd: int) -> Dict[str, Any]:
        """ウィンドウを最大化"""
        try:
            ctypes.windll.user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
            return {"success": True, "hwnd": hwnd}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── コマンド実行 ───────────────────────────────

    def execute_powershell(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        PowerShellコマンドを実行

        Args:
            command: 実行するコマンド
            timeout: タイムアウト（秒）

        Returns:
            {"success": bool, "stdout": str, "stderr": str, "return_code": int}
        """
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True, text=True, timeout=timeout,
                encoding='utf-8', errors='replace'
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"タイムアウト ({timeout}秒)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── ソフトウェア管理 ───────────────────────────

    def list_installed_apps(self, name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        winget でインストール済みアプリを一覧表示

        Args:
            name_filter: 名前フィルタ（部分一致）

        Returns:
            アプリ情報のリスト
        """
        try:
            cmd = ["winget", "list", "--accept-source-agreements"]
            if name_filter:
                cmd.extend(["--name", name_filter])

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                encoding='utf-8', errors='replace'
            )
            if result.returncode != 0:
                return [{"error": result.stderr.strip() or "winget list 失敗"}]

            # テーブル出力をパース
            lines = result.stdout.strip().split('\n')
            apps = []
            header_found = False
            for line in lines:
                if '---' in line:
                    header_found = True
                    continue
                if header_found and line.strip():
                    apps.append({"raw": line.strip()})

            return apps
        except FileNotFoundError:
            return [{"error": "winget がインストールされていません"}]
        except Exception as e:
            return [{"error": str(e)}]

    def install_app(self, app_id: str) -> Dict[str, Any]:
        """
        winget でアプリをインストール

        Args:
            app_id: winget アプリID (例: "Google.Chrome")

        Returns:
            {"success": bool, "output": str}
        """
        try:
            result = subprocess.run(
                ["winget", "install", "--id", app_id, "--accept-package-agreements",
                 "--accept-source-agreements", "--silent"],
                capture_output=True, text=True, timeout=300,
                encoding='utf-8', errors='replace'
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "インストールタイムアウト（5分）"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def uninstall_app(self, app_id: str) -> Dict[str, Any]:
        """
        winget でアプリをアンインストール

        Args:
            app_id: winget アプリID

        Returns:
            {"success": bool, "output": str}
        """
        try:
            result = subprocess.run(
                ["winget", "uninstall", "--id", app_id, "--silent"],
                capture_output=True, text=True, timeout=120,
                encoding='utf-8', errors='replace'
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── ネットワーク情報 ───────────────────────────

    def get_network_info(self) -> Dict[str, Any]:
        """
        ネットワーク接続情報を取得

        Returns:
            IPアドレス、接続状態、Tailscale情報
        """
        if not psutil:
            return {"error": "psutil が必要です"}

        try:
            interfaces = {}
            for iface, addrs in psutil.net_if_addrs().items():
                ipv4 = [a.address for a in addrs if a.family.name == 'AF_INET']
                if ipv4:
                    interfaces[iface] = {
                        "ipv4": ipv4,
                        "is_tailscale": "tailscale" in iface.lower() or ipv4[0].startswith("100."),
                    }

            stats = psutil.net_if_stats()
            for iface in interfaces:
                if iface in stats:
                    interfaces[iface]["up"] = stats[iface].isup
                    interfaces[iface]["speed_mbps"] = stats[iface].speed

            # Tailscale ステータス
            tailscale_status = None
            try:
                r = subprocess.run(
                    ["tailscale", "status", "--json"],
                    capture_output=True, text=True, timeout=5
                )
                if r.returncode == 0:
                    ts = json.loads(r.stdout)
                    tailscale_status = {
                        "self_ip": ts.get("Self", {}).get("TailscaleIPs", []),
                        "hostname": ts.get("Self", {}).get("HostName"),
                        "online": ts.get("Self", {}).get("Online", False),
                        "peer_count": len(ts.get("Peer", {})),
                    }
            except Exception:
                pass

            return {
                "interfaces": interfaces,
                "tailscale": tailscale_status,
            }
        except Exception as e:
            return {"error": str(e)}

    # ─── ディスク情報 ───────────────────────────────

    def get_disk_info(self) -> List[Dict[str, Any]]:
        """
        全ドライブのディスク情報を取得

        Returns:
            ドライブごとの使用量リスト
        """
        if not psutil:
            return [{"error": "psutil が必要です"}]

        try:
            result = []
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    result.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_gb": round(usage.used / (1024**3), 1),
                        "free_gb": round(usage.free / (1024**3), 1),
                        "percent": round(usage.percent, 1),
                    })
                except (OSError, PermissionError):
                    continue
            return result
        except Exception as e:
            return [{"error": str(e)}]

    # ─── 監視ループ ─────────────────────────────────

    def monitor_resources(self, callback=None, interval: Optional[int] = None):
        """
        リソース使用量を定期監視（ブロッキングループ）

        Args:
            callback: アラート発生時に呼ばれる関数 callback(alert_list)
            interval: 監視間隔（秒）
        """
        interval = interval or self.alerts["monitor_interval"]
        logger.info(f"リソース監視開始（{interval}秒間隔）")

        while True:
            try:
                alerts = self.check_resource_alerts()
                if alerts and callback:
                    callback(alerts)
                elif alerts:
                    for a in alerts:
                        logger.warning(f"⚠️ {a.get('metric', '?')}: {a.get('value')} (閾値: {a.get('threshold')})")
            except Exception as e:
                logger.error(f"監視エラー: {e}")

            time.sleep(interval)


# ─── CLI ────────────────────────────────────────────

if __name__ == "__main__":
    toolkit = WindowsAutomationToolkit()

    print("=== システム情報 ===")
    info = toolkit.get_system_info()
    print(json.dumps(info, indent=2, ensure_ascii=False))

    print("\n=== リソース使用量 ===")
    usage = toolkit.get_resource_usage()
    print(json.dumps(usage, indent=2, ensure_ascii=False))

    print("\n=== プロセス TOP 5 (CPU) ===")
    procs = toolkit.get_top_processes(sort_by="cpu", limit=5)
    for p in procs:
        print(f"  {p['name']:30s} CPU={p['cpu_percent']:5.1f}%  MEM={p['memory_mb']:.0f}MB")

    print("\n=== ディスク情報 ===")
    disks = toolkit.get_disk_info()
    for d in disks:
        if "error" not in d:
            print(f"  {d['device']} {d['used_gb']}/{d['total_gb']}GB ({d['percent']}%)")

    print("\n=== アラート確認 ===")
    alerts = toolkit.check_resource_alerts()
    print(f"  アラート数: {len(alerts)}")
    for a in alerts:
        print(f"  ⚠️ {a}")
