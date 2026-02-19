#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false, reportMissingTypeStubs=false
# pylint: disable=broad-exception-caught
"""
ManaOS統合サービス自動起動マネージャー
VSCode/Cursorに接続するManaOSサービスを起動・管理
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from typing import List, Dict, Any
import time
import platform
import socket
from urllib import request, error


# When executed as a script
# (python manaos_integrations/start_vscode_cursor_services.py),
# ensure repo root is on sys.path so `manaos_integrations.*` imports resolve.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from manaos_integrations._paths import OLLAMA_PORT
except Exception:
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

DEFAULT_OLLAMA_URL = f"http://127.0.0.1:{OLLAMA_PORT}"


class ManaOSServiceManager:
    """ManaOSサービスマネージャー"""

    _DEFAULT_UNIFIED_API_PORT = int(
        os.getenv("MANAOS_UNIFIED_API_PORT", "9502")
    )
    
    SERVICES = [
        {
            "name": "MRL Memory",
            "module": "mrl_memory_integration",
            "port": 5105,
            "description": "記憶管理システム"
        },
        {
            "name": "Learning System",
            "module": "learning_system_api",
            "port": 5126,
            "description": "学習・自動改善システム"
        },
        {
            "name": "LLM Routing",
            "module": "llm_routing_mcp_server.server",
            "port": 5111,
            "description": "LLMルーティング"
        },
        {
            "name": "OpenAI Router",
            "module": "start_manaos_llm_openai_router.ps1",
            "port": 5211,
            "description": "OpenAI互換LLMルーター（Auto Port）",
            "type": "powershell"
        },
        {
            "name": "Unified API",
            "module": "unified_api_server",
            "port": _DEFAULT_UNIFIED_API_PORT,
            "description": "統合API"
        },
        {
            "name": "Video Pipeline",
            "module": "video_pipeline_mcp_server",
            "port": 5112,
            "description": "動画生成パイプライン"
        },
        {
            "name": "Pico HID MCP",
            "module": "pico_hid_mcp_server",
            "port": 5136,
            "description": "マウス/キーボード操作（Pico USB HID / PCフォールバック）",
        }
    ]
    
    def __init__(self):
        self.manaos_path = Path(__file__).resolve().parent
        self.workspace_root = self.manaos_path.parent
        self.processes = {}

        # Prefer workspace venv python if present (keeps deps consistent)
        venv_python = self.workspace_root / ".venv" / "Scripts" / "python.exe"
        self.python_executable = (
            str(venv_python) if venv_python.exists() else sys.executable
        )

        # サービスログの保存先（stdout/stderr を PIPE にすると詰まり得るためファイルへ）
        self.logs_dir = self.manaos_path / "logs" / "services"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _is_port_open(
        self,
        host: str,
        port: int,
        timeout: float = 0.3,
    ) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def _get_listen_pids_windows(self, port: int) -> List[int]:
        if platform.system() != "Windows":
            return []
        try:
            cmd = (
                "Get-NetTCPConnection -LocalPort {p} -State Listen "
                "-ErrorAction SilentlyContinue "
                "| Select-Object -ExpandProperty OwningProcess -Unique "
                "| ConvertTo-Json -Compress"
            ).format(p=port)
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", cmd],
                cwd=str(self.workspace_root),
                text=True,
                errors="replace",
            ).strip()
            if not out:
                return []
            data = json.loads(out)
            if isinstance(data, list):
                return [int(x) for x in data if str(x).strip().isdigit()]
            if str(data).strip().isdigit():
                return [int(data)]
            return []
        except Exception:
            return []

    def _try_release_unified_api_port(self, port: int) -> bool:
        """Try to release Unified API port using helper script.

        Note: UAC may prompt.
        """
        script_path = self.manaos_path / "restart_unified_api_port9502.ps1"
        if not script_path.exists():
            return False

        try:
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                    "-Port",
                    str(port),
                ],
                cwd=str(self.workspace_root),
            )
        except Exception:
            return False

        # Wait a bit for UAC + kill to happen
        deadline = time.time() + 45
        while time.time() < deadline:
            if not self._is_port_open("127.0.0.1", port, timeout=0.2):
                return True
            time.sleep(2)
        return False

    def _is_unified_api_healthy(self, port: int) -> bool:
        url = f"http://127.0.0.1:{port}/health"
        try:
            req = request.Request(url, method="GET")
            with request.urlopen(req, timeout=2) as resp:
                return int(getattr(resp, "status", 0)) == 200
        except (error.URLError, OSError, TimeoutError, ValueError):
            return False

    def _get_router_port_from_status(self) -> int:
        status_file = self.manaos_path / "logs" / "manaos_llm_router_port.txt"
        if not status_file.exists():
            return 5211

        try:
            for line in status_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("port="):
                    value = line.replace("port=", "", 1).strip()
                    if value.isdigit():
                        return int(value)
        except Exception:
            pass

        return 5211

    def _is_openai_router_healthy(self, port: int) -> bool:
        url = f"http://127.0.0.1:{port}/api/llm/health"
        try:
            req = request.Request(url, method="GET")
            with request.urlopen(req, timeout=3) as resp:
                return int(getattr(resp, "status", 0)) == 200
        except (error.URLError, OSError, TimeoutError, ValueError):
            return False

    def wait_for_openai_router_health(
        self,
        retries: int = 5,
        retry_delay: int = 2,
    ) -> bool:
        """OpenAI Router のヘルス応答を待機する。"""
        for _ in range(retries):
            port = self._get_router_port_from_status()
            if self._is_openai_router_healthy(port):
                print(
                    "[OK] OpenAI Router ヘルスチェック成功 "
                    f"(http://127.0.0.1:{port}/api/llm/health)"
                )
                return True
            time.sleep(retry_delay)

        final_port = self._get_router_port_from_status()
        print(
            "[ERROR] OpenAI Router ヘルスチェック失敗 "
            f"(http://127.0.0.1:{final_port}/api/llm/health)"
        )
        return False
        
    def start_service(self, service: Dict[str, Any], retries: int = 2) -> bool:
        """サービスを起動（リトライ付き）"""
        name = service["name"]
        module = service["module"]
        port = service["port"]
        service_type = service.get("type", "python")

        def register_external_service(active_port: int) -> None:
            self.processes[name] = {
                "process": None,
                "module": module,
                "port": active_port,
                "external": True,
                "service_type": service_type,
            }

        # If port is already in use, handle Unified API specially
        if service_type == "python" and self._is_port_open(
            "127.0.0.1", port, timeout=0.2
        ):
            if name == "Unified API":
                if self._is_unified_api_healthy(port):
                    print(
                        (
                            f"[OK] {name} は既に正常稼働中です"
                            f"（ポート {port} /health=200）。スキップします。"
                        )
                    )
                    register_external_service(port)
                    return True

                print(f"[WARN] {name} のポート {port} が既に使用中です。解放を試みます...")
                # If we can see a listener PID, show it for debugging
                pids = self._get_listen_pids_windows(port)
                if pids:
                    pid_text = ", ".join(str(p) for p in pids)
                    print(f"[INFO] LISTEN PID: {pid_text}")
                if self._try_release_unified_api_port(port):
                    print(f"[OK] ポート {port} を解放しました。起動を続行します。")
                else:
                    helper = (
                        self.manaos_path / "restart_unified_api_port9502.ps1"
                    )
                    print(f"[ERROR] ポート {port} の解放に失敗しました。")
                    print(f"        管理者権限が必要な場合があります: {helper}")
                    return False
            else:
                print(f"[OK] {name} は既に起動しているようです（ポート {port}）。スキップします。")
                register_external_service(port)
                return True
        
        for attempt in range(1, retries + 1):
            print(
                f"[START] {name} を起動中... (ポート: {port}, 試行 {attempt}/{retries})"
            )
            
            try:
                # Pythonパス設定
                env = os.environ.copy()
                env["PYTHONPATH"] = str(self.manaos_path)
                # サービスが参照する標準的な PORT 環境変数をセット
                env["PORT"] = str(port)

                # pico_hid_mcp_server は PORT ではなく独自の health ポートを参照する
                if name == "Pico HID MCP":
                    env["PICO_HID_MCP_HEALTH_PORT"] = str(port)
                # localhost が IPv6 / proxy に流れて疎通に失敗する環境があるため、
                # ローカル疎通チェック用途の Ollama URL は 127.0.0.1 に固定する。
                # 特に Unified API の /ready を安定させるため、該当サービスは強制上書き。
                if name in ("Unified API", "LLM Routing"):
                    env["OLLAMA_URL"] = DEFAULT_OLLAMA_URL
                else:
                    env.setdefault("OLLAMA_URL", DEFAULT_OLLAMA_URL)
            
                # プロセス起動（Windowsではウィンドウを非表示）
                creation_flags = 0
                if platform.system() == "Windows":
                    # CREATE_NO_WINDOW フラグでコンソールウィンドウを表示しない
                    creation_flags = subprocess.CREATE_NO_WINDOW

                service_log_name = f"{name.replace(' ', '_').lower()}.log"
                service_log_path = self.logs_dir / service_log_name
                service_log_file = open(
                    service_log_path,
                    "a",
                    encoding="utf-8",
                    errors="replace",
                )

                if service_type == "powershell":
                    script_path = self.manaos_path / module
                    if not script_path.exists():
                        raise FileNotFoundError(
                            f"script not found: {script_path}"
                        )

                    proc = subprocess.Popen(
                        [
                            "powershell",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(script_path),
                            "-LlmServer",
                            "ollama",
                            "-Port",
                            str(port),
                            "-AutoSelectPort",
                        ],
                        cwd=str(self.manaos_path),
                        env=env,
                        stdout=service_log_file,
                        stderr=service_log_file,
                        creationflags=creation_flags,
                    )

                    time.sleep(4)
                    actual_port = self._get_router_port_from_status()
                    if proc.poll() is not None:
                        if (
                            proc.returncode == 0
                            and self._is_openai_router_healthy(actual_port)
                        ):
                            register_external_service(actual_port)
                            print(
                                "[OK] OpenAI Router は既存プロセスに接続しました "
                                f"(ポート {actual_port})"
                            )
                            return True

                        raise RuntimeError(
                            "OpenAI Router process exited early "
                            f"(code={proc.returncode})"
                        )

                    if not self._is_openai_router_healthy(actual_port):
                        raise RuntimeError(
                            "OpenAI Router health check failed "
                            f"on port {actual_port}"
                        )

                    port = actual_port
                else:
                    proc = subprocess.Popen(
                        [self.python_executable, "-m", module],
                        cwd=str(self.manaos_path),
                        env=env,
                        stdout=service_log_file,
                        stderr=service_log_file,
                        creationflags=creation_flags
                    )
            
                self.processes[name] = {
                    "process": proc,
                    "module": module,
                    "port": port,
                    "external": False,
                    "service_type": service_type,
                    "log_path": str(service_log_path),
                    "log_file": service_log_file,
                }
            
                print(f"[OK] {name} が起動しました (PID: {proc.pid})")
                return True
                
            except Exception as e:
                print(f"[ERROR] {name} の起動に失敗 (試行 {attempt}/{retries}): {e}")
                if attempt < retries:
                    time.sleep(2 ** attempt)  # exponential backoff
        
        return False
    
    def start_all_services(self) -> bool:
        """すべてのサービスを起動"""
        print("="*60)
        print("ManaOSサービスを起動中...")
        print("="*60)
        print()
        
        success_count = 0
        for service in self.SERVICES:
            if self.start_service(service):
                success_count += 1
            time.sleep(1)
        
        print()
        print(f"[OK] {success_count}/{len(self.SERVICES)} サービスが起動しました")
        print()
        
        return success_count == len(self.SERVICES)
    
    def stop_all_services(self):
        """すべてのサービスを停止"""
        print("\nサービスを停止中...")
        for name, info in self.processes.items():
            if info.get("external"):
                print(f"[OK] {name} は外部起動のため停止をスキップします")
                continue

            try:
                info["process"].terminate()
                info["process"].wait(timeout=5)
                print(f"[OK] {name} を停止しました")
            except Exception:
                info["process"].kill()
                print(f"[WARN] {name} を強制終了しました")

            try:
                log_file = info.get("log_file")
                if log_file:
                    log_file.close()
            except Exception:
                pass
    
    def monitor_services(self, enable_autonomous: bool = True):
        """
        サービスの状態を監視
        
        Args:
            enable_autonomous: 自律運用システムを有効化
        """
        print("\n" + "="*60)
        print("サービスの監視を開始しました (Ctrl+C で終了)")
        print("="*60)
        
        # 自律運用システムの初期化と起動
        autonomous = None
        if enable_autonomous:
            try:
                from manaos_integrations.autonomous_operations import (
                    AutonomousOperations,
                )

                autonomous = AutonomousOperations(
                    check_interval=60,  # 60秒ごとにヘルスチェック
                    enable_auto_recovery=False  # 自動復旧は無効（手動対応）
                )
                autonomous.start()
                print("[AUTO] 自律運用システム (System3) を起動しました")
            except Exception as e:
                print(f"[WARN] 自律運用システムの起動に失敗: {e}")
                print("   通常の監視モードで続行します")
        
        print()
        
        try:
            while True:
                # 各サービスのステータスを確認
                active = 0
                for name, info in self.processes.items():
                    if info.get("external"):
                        if self._is_port_open(
                            "127.0.0.1", info["port"], timeout=0.2
                        ):
                            print(f"[OK] {name}: アクティブ (ポート: {info['port']})")
                            active += 1
                        else:
                            print(f"[ERROR] {name}: 停止 (ポート: {info['port']})")
                    else:
                        if info["process"].poll() is None:
                            print(f"[OK] {name}: アクティブ (ポート: {info['port']})")
                            active += 1
                        else:
                            pid = info["process"].pid
                            print(f"[ERROR] {name}: 停止 (PID: {pid})")
                
                print(f"\n稼働中: {active}/{len(self.processes)}\n")
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n監視を終了します...")
        finally:
            # 自律運用システムの停止
            if autonomous:
                try:
                    autonomous.print_stats()
                    autonomous.stop()
                except Exception as e:
                    print(f"[WARN] 自律運用システムの停止エラー: {e}")
    
    def print_service_info(self):
        """サービス情報を表示"""
        print("\n" + "="*60)
        print("[INFO] ManaOSサービス情報")
        print("="*60)
        
        for i, service in enumerate(self.SERVICES, 1):
            print(f"\n{i}. {service['name']}")
            print(f"   モジュール: {service['module']}")
            print(f"   ポート: {service['port']}")
            print(f"   説明: {service['description']}")
        
        print("\n" + "="*60)
        print("[CONFIG] 設定ファイル:")
        print("  Cursor: ~/.cursor/mcp.json")
        print("  VSCode: ~/.vscode/settings.json")
        print(f"  ManaOS: {self.manaos_path}")
        
        print("\n" + "="*60)
        print("[CONNECT] 接続方法:")
        print("  1. 各サービスが自動で起動")
        print("  2. Cursor/VSCodeから MCPサーバーとして利用可能")
        print("  3. コード補完・エラー診断に メモリベースの提案が反映")
        
        print("\n" + "="*60)


def main():
    """メイン処理"""
    # Auto-startup 環境か判定（親プロセスが wscript.exe か svchost.exe の場合）
    parent_cmdline_local = ""
    try:
        import psutil as psutil_mod  # pyright: ignore[reportMissingTypeStubs]

        parent_proc = psutil_mod.Process(os.getppid())
        parent_cmdline_local = parent_proc.name().lower()
    except Exception:
        pass
    
    is_autostart_local = (
        "wscript" in parent_cmdline_local
        or "task" in parent_cmdline_local
    )
    
    manager = ManaOSServiceManager()
    strict_startup = os.getenv("MANAOS_STRICT_STARTUP", "1").lower() in {
        "1", "true", "yes", "on"
    }
    
    # サービス情報を表示
    manager.print_service_info()
    
    # すべてのサービスを起動
    if manager.start_all_services():
        # ヘルスチェックを実行（起動完了待ちのため数秒待機）
        print("[WAIT] サービス初期化完了を待機中... (5秒)")
        time.sleep(5)
        
        try:
            # ヘルスチェックスクリプトを実行
            from manaos_integrations.check_services_health import (
                check_all_services,
            )

            health_ok = check_all_services(retry_count=3, retry_delay=2)
            router_ok = manager.wait_for_openai_router_health(
                retries=5,
                retry_delay=2,
            )
            
            if not health_ok:
                print("[WARN] ヘルスチェックで一部のサービスが応答しませんでした")
                print("   サービスは起動していますが、初期化に時間がかかっている可能性があります")
            if not router_ok:
                print("[WARN] OpenAI Router のヘルス確認に失敗しました")

            if strict_startup and (not health_ok or not router_ok):
                print("[ERROR] strict startup mode: 必須サービスのヘルスチェック失敗")
                manager.stop_all_services()
                sys.exit(1)
        except Exception as e:
            print(f"[WARN] ヘルスチェック実行エラー: {e}")
            if strict_startup:
                print("[ERROR] strict startup mode: ヘルスチェック実行エラー")
                manager.stop_all_services()
                sys.exit(1)
        
        # Auto-startup 環境の場合はここで終了（バックグラウンドで実行続行）
        if is_autostart_local:
            print("[OK] Auto-startup: バックグラウンド実行に切り替わります (Exit)")
            sys.exit(0)
        
        # インタラクティブ実行の場合は監視を開始
        try:
            manager.monitor_services()
        except KeyboardInterrupt:
            print("\n\n停止シグナルを受け取りました...")
        finally:
            manager.stop_all_services()
            print("\n[OK] すべてのサービスを停止しました")
    else:
        print("[ERROR] サービスの起動に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    # Auto-startup: redirect output to log
    try:
        parent_cmdline_boot = ""
        try:
            import psutil as psutil_boot

            parent_boot = psutil_boot.Process(os.getppid())
            parent_cmdline_boot = parent_boot.name().lower()
        except Exception:
            pass
        
        argv_text = " ".join(sys.argv).lower()
        is_autostart = (
            "wscript" in parent_cmdline_boot
            or "task" in parent_cmdline_boot
            or "start_manaos" in argv_text
        )
        
        if is_autostart:
            # Auto-startup: suppress console output by redirecting to log
            startup_log_path = (
                Path("logs") / "start_vscode_cursor_services.log"
            )
            startup_log_path.parent.mkdir(exist_ok=True)
            try:
                startup_log_file = open(
                    startup_log_path,
                    "a",
                    encoding="utf-8",
                )
                sys.stdout = startup_log_file
                sys.stderr = startup_log_file
            except Exception:
                pass  # If cannot redirect, continue anyway
    except Exception:
        pass
    
    main()
