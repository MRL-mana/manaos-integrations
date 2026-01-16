# 🚀 Open WebUI × MCPサーバー統合計画

**作成日**: 2025-01-10

---

## ✅ 現在の状態

### Open WebUI

- ✅ **ローカル環境**: `http://localhost:3001` で動作中
- ✅ **コンテナ化**: Dockerコンテナ（`open-webui`）として実行中
- ✅ **ネットワーク**: `llm_network` に接続
- ✅ **設定**: 環境変数で設定可能

### MCPサーバー

- ✅ **manaos_unified_mcp_server**: 既に実装済み
- ✅ **30+のツール**: 画像生成、ファイル管理、ノート作成など
- ✅ **Cursor統合**: Cursorから直接使用可能

---

## 🎯 統合オプション

### オプション1: Open WebUIからMCPサーバー経由でmanaOS統合APIを使う

**方法**: Open WebUIのFunctions機能で、MCPサーバーのツールを呼び出す

**メリット**:
- ✅ 既存のMCPサーバーを活用
- ✅ CursorとOpen WebUIで同じツールを使用可能
- ✅ 統合性が高い

**実装方法**:
1. MCPサーバーのツールをOpen WebUIのFunctionsとして登録
2. または、MCPサーバーをHTTP API経由で呼び出せるようにする

---

### オプション2: Open WebUI自体をMCPサーバー経由で操作する

**方法**: MCPサーバーからOpen WebUIのAPIを呼び出す

**メリット**:
- ✅ CursorからOpen WebUIの設定を変更可能
- ✅ チャットの作成・管理が自動化可能
- ✅ モデルの切り替えが自動化可能

**実装方法**:
1. Open WebUIの管理APIをMCPツールとして追加
2. CursorからOpen WebUIを操作するツールを作成

---

### オプション3: manaOS統合APIをMCPサーバーとして公開

**方法**: manaOS統合APIをMCPサーバーとして直接公開

**メリット**:
- ✅ Cursorから直接manaOS統合APIを使用可能
- ✅ Open WebUIとは別の経路でアクセス可能
- ✅ 統合性が高い

**実装方法**:
1. 既存の`manaos_unified_mcp_server`を拡張
2. または、新しいMCPサーバーを作成

---

## 📋 推奨アプローチ

### 推奨: オプション1 + オプション2の組み合わせ

1. **MCPサーバーをHTTP API経由で呼び出せるようにする**
   - MCPサーバーのツールをREST API経由で呼び出せるようにする
   - Open WebUIのFunctionsとして登録

2. **Open WebUIをMCPサーバー経由で操作できるようにする**
   - Open WebUIの管理APIをMCPツールとして追加
   - CursorからOpen WebUIを操作可能に

---

## 🔧 実装手順（オプション1: MCPサーバーをHTTP API経由で呼び出す）

### ステップ1: MCPサーバーをHTTP APIとして公開

MCPサーバーのツールをREST API経由で呼び出せるようにする：

```python
# mcp_api_server.py
from flask import Flask, request, jsonify
from manaos_unified_mcp_server.server import call_tool

app = Flask(__name__)

@app.route("/api/mcp/tool/<tool_name>", methods=["POST"])
def call_mcp_tool(tool_name):
    """MCPツールを呼び出す"""
    data = request.json
    result = await call_tool(tool_name, data)
    return jsonify(result)
```

### ステップ2: Open WebUIのFunctionsとして登録

1. Open WebUIの設定画面を開く
2. 「Functions」タブを選択
3. 「Add Function」をクリック
4. 以下の情報を入力：

   - **Name**: `comfyui_generate_image_mcp`
   - **URL**: `http://host.docker.internal:9500/api/mcp/tool/comfyui_generate_image`
   - **Method**: `POST`

### ステップ3: チャットで使用

チャットで「画像を生成して」と入力すると、MCPサーバー経由でmanaOS統合APIが呼び出されます。

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
            "model": {"type": "string", "description": "使用するモデル"}
        },
        "required": ["message"]
    }
)
```

### ステップ2: Open WebUIのAPIを呼び出す実装

```python
async def openwebui_create_chat(arguments: dict):
    """Open WebUIでチャットを作成"""
    import requests

    url = "http://localhost:3001/api/v1/chats/new"
    headers = {"Authorization": "Bearer YOUR_API_KEY"}
    data = {
        "message": arguments.get("message"),
        "model": arguments.get("model", "qwen2.5-coder-7b-instruct")
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()
```

---

## 💡 補足: Open WebUIの管理API

Open WebUIは以下の管理APIを提供しています：

- `POST /api/v1/chats/new` - チャット作成
- `GET /api/v1/chats/` - チャット一覧取得
- `POST /api/v1/chats/{chat_id}` - チャット更新
- `GET /api/v1/models/` - モデル一覧取得

これらのAPIをMCPツールとして公開することで、CursorからOpen WebUIを操作できます。

---

## 🎯 次のステップ

どちらの統合を実装しますか？

1. **オプション1**: MCPサーバーをHTTP API経由で呼び出す（Open WebUIのFunctionsとして使用）
2. **オプション2**: Open WebUIをMCPサーバー経由で操作する（CursorからOpen WebUIを操作）
3. **両方**: 両方の統合を実装して、完全な統合を実現

---

**どれで進めますか？**
