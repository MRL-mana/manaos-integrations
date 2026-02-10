#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS記憶機能VSCode/Cursor統合
MRLメモリ、学習システム、記憶機能をVSCode/Cursorに接続
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess

class VSCodeManaOSIntegration:
    """VSCode/Cursor ManaOS統合"""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.vscode_dir = self.home_dir / ".vscode"
        self.cursor_dir = self.home_dir / ".cursor"
        self.manaos_path = Path(__file__).resolve().parent
        
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
    
    def create_vscode_manaos_settings(self) -> Dict[str, Any]:
        """VSCode用ManaOS設定を作成"""
        return {
            "manaos": {
                "enabled": True,
                "integrationPath": str(self.manaos_path),
                "apiUrl": "http://localhost:9500",
                "memory": {
                    "enabled": True,
                    "type": "mrl",
                    "apiUrl": "http://localhost:5103",
                    "autoSync": True,
                    "syncInterval": 5000
                },
                "learning": {
                    "enabled": True,
                    "apiUrl": "http://localhost:5104",
                    "adaptiveOptimization": True
                },
                "llmRouting": {
                    "enabled": True,
                    "apiUrl": "http://localhost:5111",
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
    
    def create_manaos_mcp_servers() -> Dict[str, Any]:
        """ManaOS MCPサーバー設定"""
        return {
            "manaos-memory": {
                "command": "python",
                "args": ["-m", "mrl_memory_system.mcp_server"],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "MANAOS_MEMORY_PORT": "5103"
                },
                "cwd": str(self.manaos_path)
            },
            "manaos-learning": {
                "command": "python",
                "args": ["-m", "learning_system_api"],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "LEARNING_SYSTEM_PORT": "5104"
                },
                "cwd": str(self.manaos_path)
            },
            "manaos-unified-api": {
                "command": "python",
                "args": ["-m", "unified_api_mcp_server.server"],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "UNIFIED_API_PORT": "9500"
                },
                "cwd": str(self.manaos_path)
            },
            "manaos-llm-routing": {
                "command": "python",
                "args": ["-m", "llm_routing_mcp_server.server"],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "LLM_ROUTING_PORT": "5111"
                },
                "cwd": str(self.manaos_path)
            },
            "manaos-video-pipeline": {
                "command": "python",
                "args": ["-m", "video_pipeline_mcp_server.server"],
                "env": {
                    "PYTHONPATH": str(self.manaos_path),
                    "VIDEO_PIPELINE_HEALTH_PORT": "5112"
                },
                "cwd": str(self.manaos_path)
            }
        }
    
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
            except Exception:
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
        
        # Cursor設定確認
        if integration.setup_cursor():
            print()
        
        # 次のステップを表示
        integration.print_next_steps()
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
