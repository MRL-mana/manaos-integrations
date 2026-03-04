#!/usr/bin/env python3
"""
X280クロードデスクトップ設定システム
X280環境に最適化されたクロードデスクトップの設定とMCP統合
"""

import os
import json
from pathlib import Path

class X280ClaudeDesktopSetup:
    def __init__(self):
        self.home_dir = Path.home()
        self.claude_config_dir = self.home_dir / ".config" / "claude-desktop"
        self.claude_config_dir.mkdir(parents=True, exist_ok=True)
        
        print("🚀 X280クロードデスクトップ設定システム")
        print(f"📁 設定ディレクトリ: {self.claude_config_dir}")
    
    def create_claude_desktop_config(self):
        # クロードデスクトップ設定ファイルを作成
        config = {
            "claude": {
                "apiKey": "your-claude-api-key-here",
                "model": "claude-3-5-sonnet-20241022",
                "maxTokens": 4096,
                "temperature": 0.7
            },
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/root"],
                    "env": {}
                },
                "google-drive": {
                    "command": "python3",
                    "args": ["/root/google_drive_mcp_server.py"],
                    "env": {
                        "GOOGLE_APPLICATION_CREDENTIALS": "/root/google_drive_credentials.json"
                    }
                },
                "pdf-converter": {
                    "command": "python3",
                    "args": ["/root/pdf_excel_mcp_server.py"],
                    "env": {}
                },
                "system-monitor": {
                    "command": "python3",
                    "args": ["/root/system_monitor_mcp_server.py"],
                    "env": {}
                },
                "docker-manager": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-docker"],
                    "env": {}
                },
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-github-token-here"
                    }
                },
                "google-cloud": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-google-cloud"],
                    "env": {
                        "GOOGLE_APPLICATION_CREDENTIALS": "/root/google_drive_credentials.json"
                    }
                },
                "aws": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-aws"],
                    "env": {
                        "AWS_ACCESS_KEY_ID": "your-aws-access-key",
                        "AWS_SECRET_ACCESS_KEY": "your-aws-secret-key"
                    }
                }
            },
            "ui": {
                "theme": "dark",
                "fontSize": 14,
                "windowSize": {
                    "width": 1200,
                    "height": 800
                }
            },
            "features": {
                "autoSave": True,
                "showLineNumbers": True,
                "enableMCP": True,
                "enableFileAccess": True,
                "enableSystemCommands": True
            }
        }
        
        config_file = self.claude_config_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ クロードデスクトップ設定作成完了: {config_file}")
        return config_file
    
    def create_google_drive_mcp_server(self):
        # Google Drive MCPサーバーを作成
        mcp_server_code = """#!/usr/bin/env python3
'''
Google Drive MCP Server for X280
'''

import json
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleDriveMCPServer:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.service = None
        self.credentials_file = '/root/google_drive_credentials.json'
        
    def authenticate(self):
        # Google Drive認証
        creds = None
        token_file = '/root/token.json'
        
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
    
    def list_files(self, query=''):
        # ファイル一覧取得
        try:
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)"
            ).execute()
            
            items = results.get('files', [])
            return items
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def download_file(self, file_id, destination_path):
        # ファイルダウンロード
        try:
            request = self.service.files().get_media(fileId=file_id)
            with open(destination_path, 'wb') as file:
                downloader = MediaIoBaseDownload(file, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            return True
        except HttpError as error:
            print(f'Download error: {error}')
            return False

if __name__ == "__main__":
    server = GoogleDriveMCPServer()
    server.authenticate()
    print("Google Drive MCP Server ready")
"""
        
        server_file = Path("/root/google_drive_mcp_server.py")
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(mcp_server_code)
        
        os.chmod(server_file, 0o755)
        print(f"✅ Google Drive MCPサーバー作成完了: {server_file}")
        return server_file
    
    def create_pdf_excel_mcp_server(self):
        # PDF-Excel変換MCPサーバーを作成
        mcp_server_code = """#!/usr/bin/env python3
'''
PDF-Excel変換MCP Server for X280
'''

import json
import sys
from pathlib import Path
import subprocess

class PDFExcelMCPServer:
    def __init__(self):
        self.converter_path = "/root/final_production_converter.py"
        
    def convert_pdf_to_excel(self, pdf_path, output_path=None):
        # PDFをExcelに変換
        try:
            if not output_path:
                output_path = pdf_path.replace('.pdf', '_converted.xlsx')
            
            cmd = [
                'python3', self.converter_path,
                '--input', pdf_path,
                '--output', output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output_file": output_path,
                    "message": "変換成功"
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "message": "変換失敗"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "変換エラー"
            }
    
    def batch_convert(self, input_directory, output_directory):
        # バッチ変換
        input_path = Path(input_directory)
        output_path = Path(output_directory)
        output_path.mkdir(exist_ok=True)
        
        results = []
        for pdf_file in input_path.glob("*.pdf"):
            output_file = output_path / f"{pdf_file.stem}_converted.xlsx"
            result = self.convert_pdf_to_excel(str(pdf_file), str(output_file))
            results.append({
                "input": str(pdf_file),
                "output": str(output_file),
                "result": result
            })
        
        return results

if __name__ == "__main__":
    server = PDFExcelMCPServer()
    print("PDF-Excel変換MCP Server ready")
"""
        
        server_file = Path("/root/pdf_excel_mcp_server.py")
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(mcp_server_code)
        
        os.chmod(server_file, 0o755)
        print(f"✅ PDF-Excel変換MCPサーバー作成完了: {server_file}")
        return server_file
    
    def create_system_monitor_mcp_server(self):
        # システム監視MCPサーバーを作成
        mcp_server_code = """#!/usr/bin/env python3
'''
システム監視MCP Server for X280
'''

import json
import sys
import psutil
import subprocess
from datetime import datetime

class SystemMonitorMCPServer:
    def __init__(self):
        pass  # NOTE: 初期化不要 — メソッドは直接psutilを呼び出す
    def get_system_info(self):
        # システム情報取得
        try:
            info = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "free": psutil.disk_usage('/').free,
                    "percent": psutil.disk_usage('/').percent
                },
                "network": {
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv
                },
                "timestamp": datetime.now().isoformat()
            }
            return info
        except Exception as e:
            return {"error": str(e)}
    
    def get_processes(self):
        # プロセス一覧取得
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return processes
        except Exception as e:
            return {"error": str(e)}
    
    def get_docker_status(self):
        # Dockerコンテナ状況取得
        try:
            result = subprocess.run(['docker', 'ps', '-a', '--format', 'json'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split('\\n'):
                    if line:
                        containers.append(json.loads(line))
                return containers
            else:
                return {"error": "Docker not available"}
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    server = SystemMonitorMCPServer()
    print("システム監視MCP Server ready")
"""
        
        server_file = Path("/root/system_monitor_mcp_server.py")
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(mcp_server_code)
        
        os.chmod(server_file, 0o755)
        print(f"✅ システム監視MCPサーバー作成完了: {server_file}")
        return server_file
    
    def create_startup_script(self):
        # クロードデスクトップ起動スクリプトを作成
        startup_script = """#!/bin/bash

echo "🚀 X280クロードデスクトップ起動"
echo "=" * 50

# 設定ファイル確認
if [ ! -f ~/.config/claude-desktop/config.json ]; then
    echo "❌ 設定ファイルが見つかりません"
    echo "💡 まず設定を作成してください: python3 x280_claude_desktop_setup.py"
    exit 1
fi

# MCPサーバー起動
echo "📡 MCPサーバー起動中..."
nohup python3 /root/google_drive_mcp_server.py > /tmp/google_drive_mcp.log 2>&1 &
nohup python3 /root/pdf_excel_mcp_server.py > /tmp/pdf_excel_mcp.log 2>&1 &
nohup python3 /root/system_monitor_mcp_server.py > /tmp/system_monitor_mcp.log 2>&1 &

echo "✅ MCPサーバー起動完了"

# クロードデスクトップ起動（利用可能な場合）
if command -v claude-desktop &> /dev/null; then
    echo "🚀 クロードデスクトップ起動中..."
    claude-desktop &
elif [ -f /tmp/claude-desktop.AppImage ]; then
    echo "🚀 クロードデスクトップAppImage起動中..."
    /tmp/claude-desktop.AppImage &
else
    echo "⚠️  クロードデスクトップが見つかりません"
    echo "💡 代替案:"
    echo "  - Cursor内蔵クロード使用"
    echo "  - ブラウザ版クロード使用"
    echo "  - API経由でクロード使用"
fi

echo ""
echo "🎉 X280クロードデスクトップ環境準備完了！"
echo "📊 MCPサーバー:"
echo "  - Google Drive統合: 稼働中"
echo "  - PDF-Excel変換: 稼働中"
echo "  - システム監視: 稼働中"
echo ""
echo "🌐 アクセス方法:"
echo "  - Cursor内蔵クロード"
echo "  - ブラウザ版クロード"
echo "  - MCP統合機能"
"""
        
        script_file = Path("/root/start_claude_desktop.sh")
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(startup_script)
        
        os.chmod(script_file, 0o755)
        print(f"✅ 起動スクリプト作成完了: {script_file}")
        return script_file
    
    def create_mcp_integration_guide(self):
        # MCP統合ガイドを作成
        guide_content = """# X280クロードデスクトップ MCP統合ガイド

## 🚀 概要
X280環境でクロードデスクトップとMCPサーバーを統合して使用するためのガイドです。

## 📁 設定ファイル
- 設定ディレクトリ: `~/.config/claude-desktop/`
- 設定ファイル: `config.json`
- MCPサーバー: `/root/*_mcp_server.py`

## 🔧 利用可能なMCPサーバー

### 1. Google Drive統合
- ファイル一覧取得
- ファイルダウンロード
- 認証管理

### 2. PDF-Excel変換
- PDFからExcelへの変換
- バッチ変換
- OCR機能

### 3. システム監視
- システム情報取得
- プロセス監視
- Dockerコンテナ状況

### 4. ファイルシステム
- ファイル操作
- ディレクトリ管理
- 権限管理

### 5. Docker管理
- コンテナ操作
- イメージ管理
- ネットワーク設定

### 6. GitHub統合
- リポジトリ管理
- Issue・PR管理
- コードレビュー

### 7. Google Cloud統合
- GCPサービス操作
- リソース管理
- 認証管理

### 8. AWS統合
- AWSサービス操作
- リソース管理
- 認証管理

## 🚀 起動方法

```bash
# 設定作成
python3 x280_claude_desktop_setup.py

# システム起動
./start_claude_desktop.sh
```

## 💡 使用方法

1. **クロードデスクトップ起動**
   - Cursor内蔵クロード
   - ブラウザ版クロード
   - API経由クロード

2. **MCP機能利用**
   - ファイル操作
   - Google Drive連携
   - PDF変換
   - システム監視

3. **統合機能**
   - 全機能の一元管理
   - データ連携
   - 自動化

## 🔍 トラブルシューティング

### 設定ファイルエラー
```bash
# 設定ファイル再作成
python3 x280_claude_desktop_setup.py
```

### MCPサーバーエラー
```bash
# ログ確認
tail -f /tmp/*_mcp.log

# サーバー再起動
pkill -f mcp_server
./start_claude_desktop.sh
```

### 認証エラー
```bash
# 認証情報確認
ls -la /root/*credentials*
ls -la /root/token.json
```

## 📊 パフォーマンス最適化

1. **メモリ使用量監視**
2. **CPU使用率監視**
3. **ディスク容量確認**
4. **ネットワーク状況確認**

## 🎯 今後の拡張

- 追加MCPサーバー
- カスタム機能
- 自動化ワークフロー
- 統合ダッシュボード
"""
        
        guide_file = Path("/root/X280_Claude_Desktop_Guide.md")
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print(f"✅ MCP統合ガイド作成完了: {guide_file}")
        return guide_file
    
    def setup_system(self):
        # システム全体をセットアップ
        print("\n🔄 X280クロードデスクトップセットアップ開始")
        print("=" * 60)
        
        # 1. クロードデスクトップ設定作成
        self.create_claude_desktop_config()
        
        # 2. MCPサーバー作成
        self.create_google_drive_mcp_server()
        self.create_pdf_excel_mcp_server()
        self.create_system_monitor_mcp_server()
        
        # 3. 起動スクリプト作成
        self.create_startup_script()
        
        # 4. 統合ガイド作成
        self.create_mcp_integration_guide()
        
        print("\n🎉 セットアップ完了！")
        print(f"📁 設定ディレクトリ: {self.claude_config_dir}")
        print("🚀 起動方法: ./start_claude_desktop.sh")
        print("📖 ガイド: X280_Claude_Desktop_Guide.md")
        
        return True

def main():
    print("🌟 X280クロードデスクトップ設定システム")
    print("=" * 60)
    
    setup = X280ClaudeDesktopSetup()
    success = setup.setup_system()
    
    if success:
        print("\n✅ セットアップ成功！")
        print("💡 次のステップ:")
        print("  1. ./start_claude_desktop.sh でシステム起動")
        print("  2. クロードデスクトップでMCP機能利用")
        print("  3. Google Drive、PDF変換、システム監視が利用可能")
        print("  4. 統合ガイドで詳細確認")
    else:
        print("\n❌ セットアップ失敗")

if __name__ == "__main__":
    main()
