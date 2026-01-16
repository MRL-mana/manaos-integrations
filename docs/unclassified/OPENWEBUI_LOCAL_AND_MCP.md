# ✅ Open WebUI ローカル環境 & MCPサーバー統合

**作成日**: 2025-01-10

---

## 📍 Open WebUIの環境

### 現在の状態

- ✅ **ローカル環境**: `http://localhost:3001` で動作中
- ✅ **コンテナ化**: Dockerコンテナ（`open-webui`）として実行中
- ✅ **ネットワーク**: `llm_network` に接続
- ✅ **設定可能**: 環境変数で設定変更可能

### コンテナ情報

```yaml
コンテナ名: open-webui
イメージ: ghcr.io/open-webui/open-webui:main
ポート: 3001:8080
ネットワーク: llm_network
IP: 172.20.0.2
ボリューム: openwebui_data:/app/backend/data
```

---

## 🔧 設定の変更方法

### 方法1: docker-compose.ymlで環境変数を変更

`docker-compose.always-ready-llm.yml` を編集：

```yaml
openwebui:
  environment:
    - OLLAMA_BASE_URL=http://host.docker.internal:11434
    - OPENAI_API_BASE_URL=http://host.docker.internal:1234/v1
    - OPENAI_API_KEY=lm-studio
    - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY:-your-secret-key-change-this}
    - ENABLE_SIGNUP=true
    # 新しい環境変数を追加
    - ENABLE_FUNCTIONS=true
    - ENABLE_EXTERNAL_TOOLS=true
```

変更後、コンテナを再起動：
```powershell
docker-compose -f docker-compose.always-ready-llm.yml restart openwebui
```

### 方法2: UIから設定変更

1. Open WebUIにアクセス（`http://localhost:3001`）
2. 設定画面（右上の⚙️）を開く
3. 各種設定を変更
4. 「保存」をクリック

---

## 🚀 MCPサーバーとの統合

### オプション1: MCPサーバーをHTTP API経由で呼び出す（推奨）

manaOS統合MCPサーバーのツールをREST API経由で呼び出せるようにする：

**実装**:
1. MCPサーバーのツールをREST APIとして公開
2. Open WebUIのFunctionsとして登録
3. チャットから直接使用可能

**メリット**:
- ✅ 既存のMCPサーバーを活用
- ✅ CursorとOpen WebUIで同じツールを使用可能
- ✅ 統合性が高い

---

### オプション2: Open WebUIをMCPサーバー経由で操作

CursorからOpen WebUIを操作できるMCPツールを追加：

**実装するツール**:
- `openwebui_create_chat` - チャット作成
- `openwebui_list_chats` - チャット一覧取得
- `openwebui_send_message` - メッセージ送信
- `openwebui_change_model` - モデル切り替え
- `openwebui_update_settings` - 設定変更

**メリット**:
- ✅ CursorからOpen WebUIを操作可能
- ✅ 設定変更が自動化可能
- ✅ チャット管理が自動化可能

---

### オプション3: Open WebUIをMCPサーバーとして公開

Open WebUI自体をMCPサーバーとして公開（複雑）：

**メリット**:
- ✅ Cursorから直接Open WebUIの機能を使用可能
- ✅ 統合性が高い

**デメリット**:
- ⚠️ 実装が複雑
- ⚠️ Open WebUIのAPI制限

---

## 💡 推奨アプローチ

### 推奨: オプション1 + オプション2の組み合わせ

1. **MCPサーバーのツールをREST API経由で呼び出す**
   - `manaos_unified_mcp_server` のツールをREST APIとして公開
   - Open WebUIのFunctionsとして登録

2. **Open WebUIをMCPサーバー経由で操作できるようにする**
   - Open WebUIの管理APIをMCPツールとして追加
   - CursorからOpen WebUIを操作可能に

---

## 🔧 実装手順（オプション1: MCPサーバーをHTTP API経由で呼び出す）

### ステップ1: MCPサーバーをHTTP APIとして公開

`mcp_api_server.py` を作成：

```python
from flask import Flask, request, jsonify
from manaos_unified_mcp_server.server import call_tool
import asyncio

app = Flask(__name__)

@app.route("/api/mcp/tool/<tool_name>", methods=["POST"])
def call_mcp_tool(tool_name):
    """MCPツールを呼び出す"""
    data = request.json or {}
    result = asyncio.run(call_tool(tool_name, data))
    return jsonify(result)
```

### ステップ2: docker-compose.ymlに追加

```yaml
mcp-api:
  build:
    context: .
    dockerfile: mcp_api_server/Dockerfile
  container_name: mcp-api-server
  restart: unless-stopped
  ports:
    - "9502:9502"
  environment:
    - MANAOS_API_URL=http://host.docker.internal:9500
    - COMFYUI_URL=http://host.docker.internal:8188
  extra_hosts:
    - "host.docker.internal:host-gateway"
  networks:
    - llm_network
```

### ステップ3: Open WebUIのFunctionsとして登録

1. Open WebUIの設定画面を開く
2. 「Functions」タブを選択
3. 「Add Function」をクリック
4. 以下の情報を入力：

   - **Name**: `comfyui_generate_image_mcp`
   - **URL**: `http://host.docker.internal:9502/api/mcp/tool/comfyui_generate_image`
   - **Method**: `POST`

---

## 🔧 実装手順（オプション2: Open WebUIをMCPサーバー経由で操作）

### ステップ1: Open WebUI操作用のMCPツールを追加

`manaos_unified_mcp_server/server.py` に以下を追加：

```python
Tool(
    name="openwebui_create_chat",
    description="Open WebUIでチャットを作成",
    inputSchema={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "最初のメッセージ"},
            "model": {"type": "string", "description": "使用するモデル（例: qwen2.5-coder-7b-instruct）"}
        },
        "required": ["message"]
    }
)
```

### ステップ2: 実装

```python
async def openwebui_create_chat(arguments: dict):
    """Open WebUIでチャットを作成"""
    import requests

    url = "http://localhost:3001/api/v1/chats/new"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENWEBUI_API_KEY', '')}"
    }
    data = {
        "message": arguments.get("message"),
        "model": arguments.get("model", "qwen2.5-coder-7b-instruct")
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return [TextContent(type="text", text=f"✅ チャットを作成しました\n{response.json()}")]
    else:
        return [TextContent(type="text", text=f"❌ チャット作成に失敗しました: {response.text}")]
```

---

## 📋 まとめ

### 現在の状態

- ✅ **Open WebUI**: ローカル環境でコンテナ化済み（`localhost:3001`）
- ✅ **MCPサーバー**: 既に実装済み（`manaos_unified_mcp_server`）
- ✅ **設定可能**: docker-compose.ymlで環境変数を変更可能

### 実装可能な統合

1. **MCPサーバーのツールをREST API経由で呼び出す** ← 推奨
2. **Open WebUIをMCPサーバー経由で操作する**
3. **両方の統合** ← 完全な統合

---

## 🎯 次のステップ

どちらの統合を実装しますか？

1. **オプション1**: MCPサーバーをHTTP API経由で呼び出す（Open WebUIのFunctionsとして使用）
2. **オプション2**: Open WebUIをMCPサーバー経由で操作する（CursorからOpen WebUIを操作）
3. **両方**: 両方の統合を実装して、完全な統合を実現

---

**どれで進めますか？**
