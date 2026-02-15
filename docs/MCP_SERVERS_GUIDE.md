# ManaOS MCPサーバーガイド

Model Context Protocol (MCP) サーバーの設定・開発・運用ガイドです。

## 目次
1. [MCPサーバー概要](#mcpサーバー概要)
2. [利用可能なMCPサーバー](#利用可能なmcpサーバー)
3. [MCPサーバーの作成](#mcpサーバーの作成)
4. [統合方法](#統合方法)
5. [トラブルシューティング](#トラブルシューティング)

---

## MCPサーバー概要

MCPサーバーは、VSCode/Cursor、Claude Desktop、その他のAIツールと統合できる標準化されたAPIを提供します。

### MCPの利点
- **標準化されたインターフェース**: すべてのツールで統一されたAPI
- **プラグイン可能**: 新しい機能を簡単に追加
- **ツール連携**: 複数のAIツール間でシームレスに動作
- **セキュリティ**: 明示的な権限管理

---

## 利用可能なMCPサーバー

### 1. MRL Memory MCP (ポート: 5105)

長期記憶とコンテキスト管理を提供。

**主な機能:**
- メモリの保存・検索
- コンテキスト管理
- 関連情報の自動リンク

**使用例:**
```python
import requests

# メモリ保存
response = requests.post("http://127.0.0.1:5105/store", json={
    "content": "ユーザーは Python 開発者",
    "context": "user_profile",
    "tags": ["python", "developer"]
})

# メモリ検索
response = requests.get("http://127.0.0.1:5105/search", params={
    "query": "Python",
    "limit": 5
})
```

### 2. Learning System MCP (ポート: 5126)

ユーザーの学習パターンと最適化を管理。

**主な機能:**
- 学習履歴の記録
- パフォーマンス分析
- 最適化提案

**使用例:**
```python
# 学習イベント記録
response = requests.post("http://127.0.0.1:5126/record", json={
    "event_type": "code_completion",
    "success": True,
    "duration_ms": 150
})

# 統計取得
response = requests.get("http://127.0.0.1:5126/stats")
```

### 3. LLM Routing MCP (ポート: 5111)

最適なLLMモデルを自動選択。

**主な機能:**
- タスクの複雑度分析
- モデルルーティング
- コスト最適化

**使用例:**
```python
# ルーティングリクエスト
response = requests.post("http://127.0.0.1:5111/route", json={
    "prompt": "コードをリファクタリングして",
    "difficulty": "auto",
    "preferences": {"local_only": True}
})

recommended_model = response.json()['model']
```

### 4. Video Pipeline MCP (ポート: 5112)

動画生成・編集パイプライン。

**主な機能:**
- 動画生成
- スタイル転送
- 自動編集

**使用例:**
```python
# 動画生成ジョブ作成
response = requests.post("http://127.0.0.1:5112/generate", json={
    "prompt": "サンセットの風景",
    "duration": 10,
    "style": "cinematic"
})

job_id = response.json()['job_id']

# ステータス確認
response = requests.get(f"http://127.0.0.1:5112/job/{job_id}")
```

### 5. Pico HID MCP (ポート: 5136)

Raspberry Pi Pico経由のHID操作（マウス・キーボード）。

**主な機能:**
- マウス移動・クリック
- キーボード入力
- マクロ実行

**使用例:**
```python
# マウス移動
response = requests.post("http://127.0.0.1:5136/mouse/move", json={
    "x": 100,
    "y": 200
})

# キーボード入力
response = requests.post("http://127.0.0.1:5136/keyboard/type", json={
    "text": "Hello, World!"
})
```

---

## MCPサーバーの作成

### ステップ1: テンプレート作成

```python
# my_mcp_server.py
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({"status": "healthy", "service": "My MCP Server"})

@app.route('/process', methods=['POST'])
def process_request():
    """メイン処理エンドポイント"""
    try:
        data = request.get_json()
        
        # 処理ロジック
        result = your_processing_function(data)
        
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
```

### ステップ2: 設定ファイルに追加

manaos_integration_config.json に追加:

```json
{
  "mcp_services": {
    "my_mcp_server": {
      "port": 5200,
      "name": "My MCP Server",
      "description": "カスタムMCPサーバー"
    }
  }
}
```

### ステップ3: 起動スクリプト作成

```powershell
# start_my_mcp.ps1
$env:PORT = "5200"
python my_mcp_server.py
```

### ステップ4: 依存関係定義

services_dependency.yaml に追加:

```yaml
mcp_services:
  my_mcp_server:
    port: 5200
    depends_on:
      - unified_api  # 必要に応じて
    optional_deps: []
    health_check: /health
    startup_time: 5
```

---

## 統合方法

### VSCode/Cursor統合

`.vscode/mcp.json` または Cursor設定に追加:

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "url": "http://127.0.0.1:5200",
      "timeout": 5000
    }
  }
}
```

### Claude Desktop統合

`claude_desktop_config.json` に追加:

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "python",
      "args": [
        "C:\\path\\to\\my_mcp_server.py"
      ],
      "env": {
        "PORT": "5200"
      }
    }
  }
}
```

### Unified API経由

```python
# Unified APIが自動検出
from config_loader import get_service_url

# すべてのMCPサーバーを取得
response = requests.get(f"{get_service_url('unified_api')}/mcp/list")
mcp_servers = response.json()['servers']
```

---

## ベストプラクティス

### 1. エラーハンドリング

```python
@app.route('/process', methods=['POST'])
def process_request():
    try:
        data = request.get_json()
        
        # バリデーション
        if not data or 'required_field' not in data:
            return jsonify({"error": "Missing required field"}), 400
        
        # 処理
        result = process_data(data)
        return jsonify({"success": True, "result": result})
        
    except ValueError as e:
        return jsonify({"error": f"Validation error: {e}"}), 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500
```

### 2. ログ記録

```python
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/mcp_{datetime.now():%Y%m%d}.log'),
        logging.StreamHandler()
    ]
)

@app.before_request
def log_request():
    logging.info(f"Request: {request.method} {request.path}")

@app.after_request
def log_response(response):
    logging.info(f"Response: {response.status_code}")
    return response
```

### 3. レート制限

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per minute"]
)

@app.route('/process', methods=['POST'])
@limiter.limit("10 per minute")
def process_request():
    # 処理
    pass
```

---

## トラブルシューティング

### サーバーが起動しない

```powershell
# ポートが使用中か確認
Get-NetTCPConnection -LocalPort 5200

# プロセスを強制終了
Stop-Process -Id <PID> -Force

# または
python manaos_integrations/check_and_kill_duplicate_processes.py
```

### ヘルスチェック失敗

```python
# 手動ヘルスチェック
import requests

try:
    response = requests.get("http://127.0.0.1:5200/health", timeout=3)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except requests.exceptions.ConnectionError:
    print("サーバーに接続できません")
except requests.exceptions.Timeout:
    print("タイムアウト")
```

### デバッグモード

```python
# デバッグモードで起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5200, debug=True)
```

---

## 関連リンク

- [スニペットガイド](./SNIPPETS_GUIDE.md)
- [スキルとMCP統合](./SKILLS_AND_MCP_GUIDE.md)
- [起動依存関係](./STARTUP_DEPENDENCY.md)
