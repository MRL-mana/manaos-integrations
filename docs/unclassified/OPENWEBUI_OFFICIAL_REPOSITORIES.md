# 🔥 OpenWebUI公式リポジトリ情報

## 📋 公式リポジトリ一覧

[OpenWebUI GitHub Organization](https://github.com/open-webui) から確認した重要なリポジトリ：

### 1. open-webui/open-webui (メインリポジトリ)
- **Stars**: 120k
- **最新更新**: 2026年1月10日
- **説明**: User-friendly AI Interface (Supports Ollama, OpenAI API, ...)
- **URL**: https://github.com/open-webui/open-webui
- **用途**: OpenWebUIのメインアプリケーション

### 2. open-webui/docs (公式ドキュメント)
- **Stars**: 614
- **最新更新**: 2026年1月10日
- **説明**: https://docs.openwebui.com
- **URL**: https://github.com/open-webui/docs
- **用途**: 公式ドキュメント（最新の設定方法が記載されている）

### 3. open-webui/openapi-servers (OpenAPI Tool Servers) ⭐重要⭐
- **Stars**: 800
- **最新更新**: 2025年9月25日
- **説明**: OpenAPI Tool Servers
- **URL**: https://github.com/open-webui/openapi-servers
- **用途**: **公式のOpenAPI Tool Servers参考実装**
- **内容**:
  - `filesystem` - ファイルシステム操作の参考実装
  - `weather` - 天気APIの参考実装
  - その他の参考実装

### 4. open-webui/mcpo (MCP-to-OpenAPI Proxy)
- **Stars**: 3.8k
- **最新更新**: 2025年12月8日
- **説明**: A simple, secure MCP-to-OpenAPI proxy server
- **URL**: https://github.com/open-webui/mcpo
- **用途**: MCPサーバーをOpenAPIに変換するプロキシ

### 5. open-webui/functions (Functions)
- **Stars**: 60
- **最新更新**: 2025年11月24日
- **説明**: Functions関連
- **URL**: https://github.com/open-webui/functions
- **用途**: Function Calling関連の機能

### 6. open-webui/pipelines (Pipelines)
- **Stars**: 2.2k
- **最新更新**: 2025年8月19日
- **説明**: Pipelines: Versatile, UI-Agnostic OpenAI-Compatible Plugin Framework
- **URL**: https://github.com/open-webui/pipelines
- **用途**: プラグインフレームワーク（Function Callingを含む）

---

## 🔍 重要な発見

### openapi-serversリポジトリが公式の参考実装

`open-webui/openapi-servers`リポジトリは、OpenWebUIの公式OpenAPI Tool Servers参考実装です。

このリポジトリには以下の参考実装が含まれています：

1. **filesystem** - ファイルシステム操作
   - エンドポイント: `/read_file`, `/write_file`, `/list_directory`
   - エンドポイントパスが直接パス（`/api/tools/`プレフィックスなし）

2. **weather** - 天気API
   - エンドポイント: `/forecast`
   - エンドポイントパスが直接パス（`/api/tools/`プレフィックスなし）

### 現在のTool Serverとの比較

- ✅ エンドポイントパスを公式参考実装と同じ構造に修正済み
  - `/api/tools/service_status` → `/service_status`
  - `/api/tools/check_errors` → `/check_errors`
  - `/api/tools/generate_image` → `/generate_image`

---

## 📋 公式ドキュメントの確認

公式ドキュメント（https://docs.openwebui.com）で以下の情報を確認することを推奨：

1. **External Toolsの設定方法**
   - 最新の設定手順
   - トラブルシューティング

2. **OpenAPI Tool Serversの設定方法**
   - エンドポイントの構造
   - 認証の設定
   - 接続の確認

3. **Function Callingの設定方法**
   - Function Callingの有効化
   - ツールの選択方法

---

## 🎯 次のステップ

1. **公式ドキュメントを確認**
   - https://docs.openwebui.com
   - External Toolsの最新設定方法を確認

2. **openapi-serversリポジトリを確認**
   - 公式参考実装との比較
   - 設定方法の確認

3. **OpenWebUIの「外部ツール」設定画面でTool Serverを登録**
   - URL: `http://localhost:9503`
   - OpenAPI仕様URL: `openapi.json`
   - 認証: 「なし」または「パブリック」

4. **接続状態を確認**
   - Tool Serverの接続状態が「Connected」になっているか確認

5. **「関数呼び出し」の設定を確認**
   - 「有効 (Enabled)」または「自動 (Auto)」に設定

---

## 🔥 レミ先輩の推奨

### 優先度1: 公式ドキュメントを確認

1. **https://docs.openwebui.com を確認**
   - External Toolsの最新設定方法
   - トラブルシューティングガイド

2. **openapi-serversリポジトリを確認**
   - 公式参考実装との比較
   - 設定方法の確認

### 優先度2: OpenWebUIの設定を確認

1. **「外部ツール」設定画面でTool Serverを登録**
2. **接続状態を確認**
3. **「関数呼び出し」の設定を確認**

---

**レミ先輩モード**: 公式リポジトリを確認しました！openapi-serversが公式の参考実装です。公式ドキュメントも確認することが重要！🔥
