# n8n 現状確認とMCP統合案

**確認日:** 2025-01-28

---

## ✅ 現在の状態

### コンテナ化: ✅ 完了

- **コンテナ名:** `trinity-n8n`
- **イメージ:** `n8nio/n8n:latest`
- **状態:** 起動中（22時間稼働）
- **ポート:** 5678（0.0.0.0:5678→5678/tcp）
- **健康状態:** healthy

### 実行方法

```bash
# Dockerコンテナで実行中
docker ps | grep n8n
# trinity-n8n コンテナで実行中
```

---

## ❌ MCPサーバー統合: 未実装

### 現在の統合方法

- **方法:** REST API経由（Webhook）
- **実装箇所:** `unified_api_server.py`（344-362行目）
- **連携方式:** POSTリクエストでn8n Webhook URLに通知

```python
# 現在の実装
n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
requests.post(n8n_webhook_url, json={...})
```

### MCPサーバー統合のメリット

1. **Cursorから直接操作可能**
   - ワークフローの作成・編集
   - ワークフローの実行
   - 実行履歴の確認
   - エラーの確認

2. **統合性の向上**
   - ManaOS Control APIと同様のインターフェース
   - 他のMCPサーバー（manaos-control）と統一された操作感

3. **自動化の強化**
   - Cursorから直接ワークフローをインポート
   - ワークフローの有効化・無効化
   - 実行結果の取得

---

## 🚀 MCPサーバー統合案

### 実装方法

#### 方法1: n8n専用MCPサーバーを作成（推奨）

**構成:**
```
n8n-mcp-server/
├── server.py          # MCPサーバー本体
├── tools/
│   ├── workflow.py    # ワークフロー操作ツール
│   ├── execution.py   # 実行管理ツール
│   └── webhook.py     # Webhook管理ツール
└── config.json        # 設定ファイル
```

**実装するツール:**
1. `n8n_list_workflows` - ワークフロー一覧取得
2. `n8n_create_workflow` - ワークフロー作成
3. `n8n_import_workflow` - ワークフローインポート
4. `n8n_activate_workflow` - ワークフロー有効化
5. `n8n_execute_workflow` - ワークフロー実行
6. `n8n_get_execution` - 実行結果取得
7. `n8n_list_executions` - 実行履歴取得

#### 方法2: manaos-controlにn8n機能を追加

**メリット:**
- 既存のMCPサーバーを拡張
- 統一されたインターフェース

**デメリット:**
- manaos-controlの責務が増える
- n8n専用の機能が混在

---

## 📋 実装手順

### ステップ1: n8n MCPサーバーの作成

```python
# n8n_mcp_server/server.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import requests

server = Server("n8n-mcp")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="n8n_list_workflows",
            description="n8nのワークフロー一覧を取得",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        # ... 他のツール
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "n8n_list_workflows":
        # n8n APIを呼び出し
        response = requests.get(
            "http://100.93.120.33:5678/api/v1/workflows",
            headers={"X-N8N-API-KEY": os.getenv("N8N_API_KEY")}
        )
        return [TextContent(type="text", text=response.json())]
    # ... 他のツールの処理
```

### ステップ2: CursorのMCP設定に追加

```json
{
  "mcpServers": {
    "n8n": {
      "command": "python",
      "args": ["-m", "n8n_mcp_server"],
      "env": {
        "N8N_BASE_URL": "http://100.93.120.33:5678",
        "N8N_API_KEY": "your-api-key"
      }
    }
  }
}
```

### ステップ3: 統合APIサーバーとの連携

- MCPサーバー経由でワークフローを操作
- 統合APIサーバーからMCPサーバーを呼び出し（オプション）

---

## 🎯 実装の優先度

### 高優先度（すぐに実装）

1. **ワークフローインポート機能**
   - 現在の課題（手動インポートが必要）を解決
   - Cursorから直接インポート可能に

2. **ワークフロー有効化機能**
   - インポート後に自動で有効化

### 中優先度（後で実装）

3. **ワークフロー実行機能**
   - Cursorから直接ワークフローを実行

4. **実行履歴確認機能**
   - 実行結果をCursorで確認

### 低優先度（将来の拡張）

5. **ワークフロー編集機能**
   - Cursorからワークフローを編集（複雑）

---

## 💡 実装の判断

### 今すぐ実装する場合

**メリット:**
- ワークフローインポートが自動化される
- 100%完了への道が開ける
- Cursorからの操作が統一される

**所要時間:** 約1-2時間

### 後で実装する場合

**現状維持:**
- ブラウザで手動インポート（2分で完了）
- REST API経由の連携は既に動作中

**判断基準:**
- ワークフローインポートの頻度
- Cursorからの操作の必要性
- 自動化の優先度

---

## 📊 現在の統合状況

| 項目 | 状態 | 方法 |
|------|------|------|
| コンテナ化 | ✅ 完了 | Docker（trinity-n8n） |
| REST API連携 | ✅ 完了 | Webhook経由 |
| MCPサーバー統合 | ❌ 未実装 | - |
| ワークフローインポート | ⚠️ 手動 | ブラウザでインポート |

---

## 🚀 次のアクション

### オプション1: MCPサーバーを実装（推奨）

```bash
# n8n MCPサーバーを作成
mkdir n8n_mcp_server
cd n8n_mcp_server
# 実装開始
```

### オプション2: 現状維持

- ブラウザで手動インポート（2分）
- REST API経由の連携は既に動作中

---

**どちらで進めますか？**

1. **MCPサーバーを実装** → 自動化が強化される
2. **現状維持** → 手動インポートで100%完了


















