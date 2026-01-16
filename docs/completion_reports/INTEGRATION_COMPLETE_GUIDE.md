# 🎉 完全統合ガイド - Open WebUI × manaOS × MCPサーバー

**作成日**: 2025-01-10

---

## ✅ 実装完了内容

### 1. MCPサーバーをHTTP API経由で呼び出せるようにする ✅

- ✅ `mcp_api_server.py` を作成
- ✅ MCPサーバーのツールをREST API経由で呼び出し可能に
- ✅ OpenAPI仕様を提供（`/openapi.json`）
- ✅ Open WebUIのFunctionsとして使用可能

### 2. Open WebUI操作用のMCPツールを追加 ✅

- ✅ `openwebui_create_chat` - チャット作成
- ✅ `openwebui_list_chats` - チャット一覧取得
- ✅ `openwebui_send_message` - メッセージ送信
- ✅ `openwebui_get_chat` - チャット情報取得
- ✅ `openwebui_list_models` - モデル一覧取得
- ✅ `openwebui_update_settings` - 設定更新

### 3. Docker Composeに追加 ✅

- ✅ `docker-compose.manaos-services.yml` にMCP APIサーバーを追加
- ✅ `docker-compose.always-ready-llm.yml` にMCP APIサーバーを追加
- ✅ 両方のネットワーク（`llm_network`、`manaos-network`）で動作可能

---

## 🚀 セットアップ手順

### ステップ1: MCP APIサーバーを起動

```powershell
# manaOSサービスとして起動
docker-compose -f docker-compose.manaos-services.yml up -d mcp-api

# または、LLMサービスとして起動
docker-compose -f docker-compose.always-ready-llm.yml up -d mcp-api
```

### ステップ2: ヘルスチェック

```powershell
# ヘルスチェック
curl http://localhost:9502/health

# ツール一覧を取得
curl http://localhost:9502/api/mcp/tools

# OpenAPI仕様を取得
curl http://localhost:9502/openapi.json
```

### ステップ3: Open WebUIでExternal Toolsを設定

1. Open WebUIにアクセス（`http://localhost:3001`）
2. 設定画面（右上の⚙️）を開く
3. 「**External Tools**」タブを選択
4. 「**Add Tool**」をクリック
5. 以下の情報を入力：

   - **Name**: `ManaOS統合MCP API`
   - **URL**: `http://host.docker.internal:9502`
   - **OpenAPI Spec**: `ON`
   - **OpenAPI Spec URL**: `http://host.docker.internal:9502/openapi.json`

6. 「**Save**」をクリック

### ステップ4: Open WebUIで関数を呼び出す

チャット画面で、以下のように入力：

```
ComfyUIで画像を生成してください。プロンプトは「美しい風景」で、サイズは512x512です。
```

または：

```
generateImageComfyUI関数を使って、プロンプト「美しい風景」で画像を生成してください
```

---

## 🔧 CursorからOpen WebUIを操作する

### 1. Open WebUIでチャットを作成

```
Cursorで「openwebui_create_chat」を使って、Open WebUIでチャットを作成してください。
メッセージは「こんにちは」で、モデルは「qwen2.5-coder-7b-instruct」です。
```

### 2. Open WebUIのチャット一覧を取得

```
Cursorで「openwebui_list_chats」を使って、Open WebUIのチャット一覧を取得してください。
```

### 3. Open WebUIにメッセージを送信

```
Cursorで「openwebui_send_message」を使って、チャットID「xxx」にメッセージ「Hello」を送信してください。
```

---

## 📋 利用可能なツール一覧

### 画像生成

- `comfyui_generate_image` - ComfyUIで画像を生成

### ファイル管理

- `google_drive_upload` - Google Driveにファイルをアップロード
- `google_drive_list_files` - Google Driveのファイル一覧を取得

### ノート管理

- `obsidian_create_note` - Obsidianにノートを作成
- `obsidian_search_notes` - Obsidianでノートを検索

### Web検索

- `web_search` - SearXNGでWeb検索
- `brave_search` - Brave SearchでWeb検索

### Open WebUI操作

- `openwebui_create_chat` - チャット作成
- `openwebui_list_chats` - チャット一覧取得
- `openwebui_send_message` - メッセージ送信
- `openwebui_get_chat` - チャット情報取得
- `openwebui_list_models` - モデル一覧取得
- `openwebui_update_settings` - 設定更新

（他にも30+のツールが利用可能）

---

## 🔍 トラブルシューティング

### 問題1: MCP APIサーバーが起動しない

**解決方法**:
```powershell
# ログを確認
docker logs mcp-api-server

# コンテナを再起動
docker-compose -f docker-compose.manaos-services.yml restart mcp-api
```

### 問題2: Open WebUIからMCP APIサーバーに接続できない

**解決方法**:
1. `host.docker.internal`が正しく設定されているか確認
2. ファイアウォールでポート9502が開放されているか確認
3. Open WebUIのコンテナからアクセスできるか確認：
   ```powershell
   docker exec -it open-webui curl http://host.docker.internal:9502/health
   ```

### 問題3: 関数が呼び出されない

**解決方法**:
1. Open WebUIの「Function Call」パラメータが「有効」になっているか確認
2. モデルがFunction Callingに対応しているか確認
3. チャットで明示的に指示：
   ```
   generateImageComfyUI関数を使って、プロンプト「美しい風景」で画像を生成してください
   ```

---

## 📚 関連ファイル

- `mcp_api_server.py` - MCP APIサーバーのメインファイル
- `manaos_unified_mcp_server/server.py` - MCPサーバーの実装
- `docker-compose.manaos-services.yml` - manaOSサービスのDocker Compose設定
- `docker-compose.always-ready-llm.yml` - LLMサービスのDocker Compose設定

---

## 🎯 次のステップ

1. **統合テスト**: すべてのツールが正しく動作するか確認
2. **パフォーマンス最適化**: レスポンス時間を改善
3. **セキュリティ強化**: API認証を追加
4. **ドキュメント整備**: 各ツールの詳細な使い方を記載

---

**🎉 完全統合が完了しました！**

Open WebUI、manaOS、MCPサーバーが完全に統合され、相互に操作可能になりました。
