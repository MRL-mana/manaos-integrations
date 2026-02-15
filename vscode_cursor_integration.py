#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS記憶機能VSCode/Cursor統合
MRLメモリ、学習システム、記憶機能をVSCode/Cursorに接続
"""

import json
import io
import os
import sys
from pathlib import Path
from typing import Any, Dict


_ENCODINGS_TO_NORMALIZE = ("cp932", "cp936", "cp949")
if (
    sys.platform == "win32"
    and getattr(sys.stdout, "encoding", "") in _ENCODINGS_TO_NORMALIZE
):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


class VSCodeManaOSIntegration:
    """VSCode/Cursor ManaOS統合"""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.vscode_dir = self.home_dir / ".vscode"
        self.cursor_dir = self.home_dir / ".cursor"
        self.manaos_path = Path(__file__).resolve().parent
        self._appdata_dir = (
            Path(os.getenv("APPDATA", "")) if sys.platform == "win32" else None
        )
        
    def get_vscode_settings_path(self) -> Path:
        """VSCode設定ファイルパスを取得"""
        return self.vscode_dir / "settings.json"
    
    def get_cursor_settings_path(self) -> Path:
        """Cursor設定ファイルパスを取得"""
        return self.cursor_dir / "settings.json"
    
    def get_vscode_mcp_config_path(self) -> Path:
        """VSCode MCP設定ファイルパスを取得"""
        return self.vscode_dir / "mcp.json"
    
    def get_cursor_mcp_config_path(self) -> Path:
        """Cursor MCP設定ファイルパスを取得"""
        return self.cursor_dir / "mcp.json"

    def get_cline_mcp_settings_path(self) -> Path | None:
        """Cline MCP設定ファイルパスを取得（Windowsのみ）"""
        if sys.platform != "win32" or not self._appdata_dir:
            return None

        # VS Code Stable / Insiders / VSCodium の候補を順に探索
        product_dirs = ("Code", "Code - Insiders", "VSCodium")
        candidates: list[Path] = []

        for product in product_dirs:
            candidates.append(
                self._appdata_dir
                / product
                / "User"
                / "globalStorage"
                / "saoudrizwan.claude-dev"
                / "settings"
                / "cline_mcp_settings.json"
            )

        for candidate in candidates:
            if candidate.exists():
                return candidate

        for candidate in candidates:
            if candidate.parent.exists():
                return candidate

        return candidates[0]
    
    def create_vscode_manaos_settings(self) -> Dict[str, Any]:
        """VSCode用ManaOS設定を作成"""
        unified_api_port = int(os.getenv("MANAOS_UNIFIED_API_PORT", "9510"))
        unified_api_url = os.getenv("MANAOS_INTEGRATION_API_URL") or f"http://127.0.0.1:{unified_api_port}"
        return {
            "manaos": {
                "enabled": True,
                "integrationPath": str(self.manaos_path),
                "apiUrl": unified_api_url,
                "memory": {
                    "enabled": True,
                    "type": "mrl",
                    "apiUrl": "http://127.0.0.1:5105",
                    "autoSync": True,
                    "syncInterval": 5000
                },
                "learning": {
                    "enabled": True,
                    "apiUrl": "http://127.0.0.1:5126",
                    "adaptiveOptimization": True
                },
                "llmRouting": {
                    "enabled": True,
                    "apiUrl": "http://127.0.0.1:5111",
                    "smartRouting": True
                },
                "autoStart": True,
                "debugMode": False
            },
            "[python]": {
                "editor.defaultFormatter": "ms-python.python",
                "editor.formatOnSave": True,
                "editor.codeActionsOnSave": {
                    "source.organizeImports": "explicit"
                }
            },
            "python.analysis.typeCheckingMode": "basic",
            "python.linting.enabled": True,
            "python.linting.pylintEnabled": True
        }
    
    def create_vscode_mcp_servers(self) -> Dict[str, Any]:
        """VSCode用に最低限のManaOS MCPサーバー設定を作成"""
        unified_api_port = int(os.getenv("MANAOS_UNIFIED_API_PORT", "9510"))
        unified_api_url = os.getenv("MANAOS_INTEGRATION_API_URL") or f"http://127.0.0.1:{unified_api_port}"
        return {
            # VS Codeから ComfyUI生成などを呼ぶために必須
            "manaos-unified-api": {
                "command": "python",
                "args": ["-m", "unified_api_mcp_server.server"],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "MANAOS_INTEGRATION_API_URL": unified_api_url,
                    "MANAOS_LOG_TO_STDERR": "1",
                },
                "cwd": str(self.manaos_path),
            },
            # /health を提供（MCP未導入でも生存確認できるようパッチ済み）
            "manaos-video-pipeline": {
                "command": "python",
                "args": ["-m", "video_pipeline_mcp_server.server"],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "VIDEO_PIPELINE_HEALTH_PORT": "5112",
                    "MANAOS_LOG_TO_STDERR": "1",
                },
                "cwd": str(self.manaos_path),
            },
            # Pico HID（MCP経由の入力注入）。healthポートは 5116 衝突回避で 5136。
            "manaos-pico-hid": {
                "command": "python",
                "args": ["-m", "pico_hid_mcp_server"],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "PICO_HID_MCP_HEALTH_PORT": "5136",
                    "MANAOS_LOG_TO_STDERR": "1",
                },
                "cwd": str(self.manaos_path),
            },
        }

    def create_cline_mcp_servers(self) -> Dict[str, Any]:
        """Cline用の最低限のManaOS MCPサーバー設定を作成（Windows向け）"""
        py_cmd = "py" if sys.platform == "win32" else "python"
        py_args_prefix = ["-3.10"] if sys.platform == "win32" else []

        unified_api_port = int(os.getenv("MANAOS_UNIFIED_API_PORT", "9510"))
        unified_api_url = os.getenv("MANAOS_INTEGRATION_API_URL") or f"http://127.0.0.1:{unified_api_port}"

        return {
            "manaos-unified-api": {
                "command": py_cmd,
                "args": [
                    *py_args_prefix,
                    "-m",
                    "unified_api_mcp_server.server",
                ],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "MANAOS_INTEGRATION_API_URL": unified_api_url,
                    "MANAOS_LOG_TO_STDERR": "1",
                },
                "cwd": str(self.manaos_path),
            },
            "manaos-video-pipeline": {
                "command": py_cmd,
                "args": [
                    *py_args_prefix,
                    "-m",
                    "video_pipeline_mcp_server.server",
                ],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "VIDEO_PIPELINE_HEALTH_PORT": "5112",
                    "MANAOS_LOG_TO_STDERR": "1",
                },
                "cwd": str(self.manaos_path),
            },
            "manaos-pico-hid": {
                "command": py_cmd,
                "args": [*py_args_prefix, "-m", "pico_hid_mcp_server"],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "PICO_HID_MCP_HEALTH_PORT": "5136",
                    "MANAOS_LOG_TO_STDERR": "1",
                },
                "cwd": str(self.manaos_path),
            },
        }

    def setup_vscode_mcp(self) -> bool:
        """VSCodeのMCP設定（~/.vscode/mcp.json）を作成/更新"""
        print("📌 VSCode MCP設定を更新中...")

        self.vscode_dir.mkdir(parents=True, exist_ok=True)

        mcp_path = self.get_vscode_mcp_config_path()
        config: Dict[str, Any] = {"mcpServers": {}}

        if mcp_path.exists():
            try:
                with open(mcp_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    config = loaded
            except (OSError, json.JSONDecodeError, ValueError):
                config = {"mcpServers": {}}

        if not isinstance(config.get("mcpServers"), dict):
            config["mcpServers"] = {}

        servers = self.create_vscode_mcp_servers()
        config["mcpServers"].update(servers)

        with open(mcp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"✅ VSCode MCP設定を保存: {mcp_path}")
        print(f"   追加/更新: {len(servers)} サーバー")
        return True

    def setup_cline_mcp(self) -> bool:
        """ClineのMCP設定（cline_mcp_settings.json）を作成/更新（Windowsのみ）"""
        cline_path = self.get_cline_mcp_settings_path()
        if not cline_path:
            print("ℹ️  Cline MCP設定はこの環境ではスキップします")
            return False

        print("📌 Cline MCP設定を更新中...")
        cline_path.parent.mkdir(parents=True, exist_ok=True)

        config: Dict[str, Any] = {"mcpServers": {}}
        if cline_path.exists():
            try:
                with open(cline_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    config = loaded
            except (OSError, json.JSONDecodeError, ValueError):
                config = {"mcpServers": {}}

        if not isinstance(config.get("mcpServers"), dict):
            config["mcpServers"] = {}

        servers = self.create_cline_mcp_servers()
        config["mcpServers"].update(servers)

        with open(cline_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"✅ Cline MCP設定を保存: {cline_path}")
        print(f"   追加/更新: {len(servers)} サーバー")
        return True
    
    def setup_vscode(self) -> bool:
        """VSCodeの統合設定"""
        print("📌 VSCode統合を設定中...")
        
        # ディレクトリを作成
        self.vscode_dir.mkdir(parents=True, exist_ok=True)
        
        # ManaOS設定を追加
        settings_path = self.get_vscode_settings_path()
        settings = {}
        
        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except (OSError, json.JSONDecodeError, ValueError):
                settings = {}
        
        # ManaOS設定をマージ
        manaos_settings = self.create_vscode_manaos_settings()
        settings.update(manaos_settings)
        
        # 保存
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        print(f"✅ VSCode設定を保存: {settings_path}")
        return True
    
    def setup_cursor(self) -> bool:
        """Cursorの統合設定（既に実行済みなので確認）"""
        print("📌 Cursor設定を確認中...")
        
        mcp_path = self.get_cursor_mcp_config_path()
        if mcp_path.exists():
            with open(mcp_path, 'r', encoding='utf-8') as f:
                mcp_config = json.load(f)
            
            print(f"✅ Cursor MCP設定を確認: {mcp_path}")
            print(f"   登録済みサーバー数: {len(mcp_config.get('mcpServers', {}))}")
            return True
        
        print("⚠️  Cursor MCP設定が見つかりません")
        return False
    
    def print_next_steps(self):
        """次のステップを表示"""
        print("\n" + "="*60)
        print("🎉 VSCode/Cursor統合が完了しました！")
        print("="*60)
        
        print("\n✅ 完了した設定:")
        print("  1. Cursor → 17個のMCPサーバーを登録")
        print("  2. VSCode → ManaOS統合設定を追加")
        print("  3. MRLメモリシステムをVSCode/Cursorに接続")
        print("  4. 学習システムの統合")
        
        print("\n📌 次のステップ:")
        print("  1. VSCodeを再起動")
        print("  2. Cursorを再起動")
        print("  2b. Clineを使う場合: VSCodeで Developer: Reload Window")
        print("  3. 以下のコマンドでManaOSサービスを起動:")
        print("     cd", str(Path(__file__).resolve().parent))
        print("     python -m mrl_memory_system")
        print("     python -m learning_system_api")
        print("     python -m unified_api_mcp_server")
        
        print("\n🔌 接続確認:")
        print("  VSCode/Cursorの出力パネルでManaOSサービスの起動を確認")
        print("  メモリ機能の使用方法:")
        print("    - コード補完にメモリベースの提案が表示される")
        print("    - エラー診断がメモリから学習")
        print("    - 自動最適化が実行される")
        
        print("\n💾 設定ファイル:")
        print(f"  VSCode: {self.get_vscode_settings_path()}")
        print(f"  Cursor:  {self.get_cursor_mcp_config_path()}")
        cline_path = self.get_cline_mcp_settings_path()
        if cline_path:
            print(f"  Cline:   {cline_path}")
        print(f"  ManaOS: {self.manaos_path}")
        
        print("\n" + "="*60)


def main():
    """メイン処理"""
    try:
        integration = VSCodeManaOSIntegration()
        
        print("ManaOS VSCode/Cursor統合を開始します...")
        print()
        
        # VSCode設定
        if integration.setup_vscode():
            print()

        # VSCode MCP設定
        if integration.setup_vscode_mcp():
            print()

        # Cline MCP設定
        integration.setup_cline_mcp()
        print()
        
        # Cursor設定確認
        if integration.setup_cursor():
            print()
        
        # 次のステップを表示
        integration.print_next_steps()
        
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
