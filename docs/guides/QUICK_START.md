# 🚀 クイックスタートガイド - 完全統合

**作成日**: 2025-01-10

---

## ✅ 実装完了内容

すべての統合が完了しました！

1. ✅ **MCPサーバーをHTTP API経由で呼び出せるようにする**
2. ✅ **Open WebUI操作用のMCPツールを追加**
3. ✅ **Docker Composeに追加**

---

## 🚀 5分で始める

### ステップ1: MCP APIサーバーを起動

```powershell
# LLMサービスとして起動（推奨）
docker-compose -f docker-compose.always-ready-llm.yml up -d mcp-api

# または、manaOSサービスとして起動
docker-compose -f docker-compose.manaos-services.yml up -d mcp-api
```

### ステップ2: 動作確認

```powershell
# テストスクリプトを実行
python test_mcp_api_integration.py

# または、手動で確認
curl http://127.0.0.1:9502/health
curl http://127.0.0.1:9502/api/mcp/tools
curl http://127.0.0.1:9502/openapi.json
```

### ステップ3: Open WebUIで設定

1. Open WebUIにアクセス: `http://127.0.0.1:3001`
2. 設定画面（右上の⚙️）を開く
3. 「**External Tools**」タブを選択
4. 「**Add Tool**」をクリック
5. 以下の情報を入力：

   - **Name**: `ManaOS統合MCP API`
   - **URL**: `http://host.docker.internal:9502`
   - **OpenAPI Spec**: `ON`
   - **OpenAPI Spec URL**: `http://host.docker.internal:9502/openapi.json`

6. 「**Save**」をクリック

### ステップ4: チャットで試す

Open WebUIのチャット画面で、以下のように入力：

```
ComfyUIで画像を生成してください。プロンプトは「美しい風景」で、サイズは512x512です。
```

または、Cursorで試す：

```
Cursorで「openwebui_create_chat」を使って、Open WebUIでチャットを作成してください。
メッセージは「こんにちは」です。
```

---

## 📋 利用可能な機能

### Open WebUIから使用可能

- ✅ 画像生成（ComfyUI）
- ✅ ファイル管理（Google Drive）
- ✅ ノート作成（Obsidian）
- ✅ Web検索（SearXNG / Brave Search）
- ✅ その他30+のツール

### Cursorから使用可能

- ✅ Open WebUIのチャット作成・管理
- ✅ Open WebUIのモデル切り替え
- ✅ Open WebUIの設定変更
- ✅ その他30+のmanaOS統合ツール

---

## 🔍 トラブルシューティング

### MCP APIサーバーが起動しない

```powershell
# ログを確認
docker logs mcp-api-server

# コンテナを再起動
docker-compose -f docker-compose.always-ready-llm.yml restart mcp-api
```

### Open WebUIから接続できない

```powershell
# Open WebUIのコンテナからアクセスできるか確認
docker exec -it open-webui curl http://host.docker.internal:9502/health
```

### 関数が呼び出されない

1. Open WebUIの「Function Call」パラメータが「有効」になっているか確認
2. モデルがFunction Callingに対応しているか確認
3. チャットで明示的に指示

---

## 📚 詳細ドキュメント

- `INTEGRATION_COMPLETE_GUIDE.md` - 完全統合ガイド
- `OPENWEBUI_LOCAL_AND_MCP.md` - Open WebUIとMCPサーバーの統合について
- `test_mcp_api_integration.py` - テストスクリプト

---

**🎉 準備完了！すぐに使えます！**
