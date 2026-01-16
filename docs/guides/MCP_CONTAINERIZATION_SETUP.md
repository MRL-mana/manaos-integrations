# MCPサーバー化・コンテナ化セットアップガイド

**作成日**: 2025-01-28  
**状態**: ✅ 実装完了

---

## 📦 実装内容

### ✅ MCPサーバー化完了

1. **Unified API Server MCP** (`unified_api_mcp_server/`)
   - Unified API Serverのすべての機能をMCPツールとして提供
   - 30以上のツールを実装

2. **Step Deep Research Service MCP** (`step_deep_research_mcp_server/`)
   - 深いリサーチ機能をMCPツールとして提供
   - リサーチジョブの作成・実行・ステータス確認

3. **Gallery API Server MCP** (`gallery_api_mcp_server/`)
   - 画像生成・管理機能をMCPツールとして提供
   - 画像生成、ジョブステータス確認、画像一覧取得

4. **System Status API MCP** (`system_status_mcp_server/`)
   - システムステータス監視機能をMCPツールとして提供
   - 全サービスのステータス確認、システムリソース情報取得

5. **SSOT API MCP** (`ssot_mcp_server/`)
   - Single Source of Truth機能をMCPツールとして提供
   - SSOTデータ取得、サマリー取得、サービス状態取得

6. **Service Monitor MCP** (`service_monitor_mcp_server/`)
   - サービス監視機能をMCPツールとして提供
   - 監視ステータス取得

### ✅ コンテナ化完了

1. **Unified API Server** (`unified_api_server/Dockerfile`)
   - ポート: 9500
   - FlaskベースのAPIサーバー

2. **Step Deep Research Service** (`step_deep_research_service/Dockerfile`)
   - ポート: 5121
   - リサーチサービス

3. **Gallery API Server** (`gallery_api_server/Dockerfile`)
   - ポート: 5559
   - 画像生成・管理サービス

4. **System Status API** (`system_status_api/Dockerfile`)
   - ポート: 5112
   - システムステータス監視API

5. **SSOT API** (`ssot_api/Dockerfile`)
   - ポート: 5120
   - Single Source of Truth API

6. **Service Monitor** (`service_monitor/Dockerfile`)
   - ポート: 5111
   - サービス監視システム

---

## 🚀 セットアップ方法

### 1. MCPサーバーのセットアップ

#### Unified API Server MCP

```bash
cd unified_api_mcp_server
pip install -r requirements.txt
python -m unified_api_mcp_server.server
```

#### Step Deep Research Service MCP

```bash
cd step_deep_research_mcp_server
pip install -r requirements.txt
python -m step_deep_research_mcp_server.server
```

#### Gallery API Server MCP

```bash
cd gallery_api_mcp_server
pip install -r requirements.txt
python -m gallery_api_mcp_server.server
```

### 2. CursorでのMCPサーバー設定

`.cursor/mcp.json` または Cursorの設定に以下を追加：

```json
{
  "mcpServers": {
    "unified-api": {
      "command": "python",
      "args": ["-m", "unified_api_mcp_server.server"],
      "env": {
        "MANAOS_INTEGRATION_API_URL": "http://localhost:9500"
      }
    },
    "step-deep-research": {
      "command": "python",
      "args": ["-m", "step_deep_research_mcp_server.server"],
      "env": {
        "STEP_DEEP_RESEARCH_URL": "http://localhost:5121"
      }
    },
    "gallery-api": {
      "command": "python",
      "args": ["-m", "gallery_api_mcp_server.server"],
      "env": {
        "GALLERY_API_URL": "http://localhost:5559"
      }
    },
    "system-status": {
      "command": "python",
      "args": ["-m", "system_status_mcp_server.server"],
      "env": {
        "SYSTEM_STATUS_URL": "http://localhost:5112"
      }
    },
    "ssot-api": {
      "command": "python",
      "args": ["-m", "ssot_mcp_server.server"],
      "env": {
        "SSOT_API_URL": "http://localhost:5120"
      }
    },
    "service-monitor": {
      "command": "python",
      "args": ["-m", "service_monitor_mcp_server.server"],
      "env": {
        "SERVICE_MONITOR_URL": "http://localhost:5111"
      }
    }
  }
}
```

### 3. Docker Composeでの起動

```bash
# すべてのサービスを起動
docker-compose -f docker-compose.manaos-services.yml up -d

# 個別に起動
docker-compose -f docker-compose.manaos-services.yml up -d unified-api
docker-compose -f docker-compose.manaos-services.yml up -d step-deep-research
docker-compose -f docker-compose.manaos-services.yml up -d gallery-api

# ログ確認
docker-compose -f docker-compose.manaos-services.yml logs -f

# 停止
docker-compose -f docker-compose.manaos-services.yml down
```

---

## 📋 利用可能なMCPツール

### Unified API Server MCP

#### ヘルスチェック・ステータス
- `unified_api_health` - ヘルスチェック
- `unified_api_status` - 詳細ステータス
- `unified_api_integrations_status` - 統合モジュール状態

#### ComfyUI画像生成
- `comfyui_generate_image` - 画像生成

#### SVI動画生成
- `svi_generate_video` - 動画生成
- `svi_extend_video` - 動画延長
- `svi_get_queue_status` - キュー状態
- `svi_get_history` - 生成履歴

#### Google Drive
- `google_drive_upload` - ファイルアップロード

#### CivitAI
- `civitai_search` - モデル検索

#### 検索エンジン
- `searxng_search` - SearXNG検索
- `brave_search` - Brave Search検索

#### Base AI
- `base_ai_chat` - Base AIチャット

#### Obsidian
- `obsidian_create_note` - ノート作成

#### 記憶システム
- `memory_store` - 情報保存
- `memory_recall` - 情報検索

#### 通知システム
- `notification_send` - 通知送信

#### 秘書機能
- `secretary_morning_routine` - 朝のルーチン
- `secretary_noon_routine` - 昼のルーチン
- `secretary_evening_routine` - 夜のルーチン

#### キャッシュ・パフォーマンス
- `cache_stats` - キャッシュ統計
- `performance_stats` - パフォーマンス統計

### Step Deep Research Service MCP

- `step_deep_research_health` - ヘルスチェック
- `step_deep_research_create` - リサーチジョブ作成
- `step_deep_research_execute` - リサーチジョブ実行
- `step_deep_research_status` - リサーチジョブステータス

### Gallery API Server MCP

- `gallery_api_health` - ヘルスチェック
- `gallery_generate_image` - 画像生成
- `gallery_get_job_status` - ジョブステータス
- `gallery_list_images` - 画像一覧

### System Status API MCP

- `system_status_health` - ヘルスチェック
- `system_status_get_all` - 全サービスのステータス取得
- `system_status_get_simple` - 簡易ステータス取得
- `system_status_get_resources` - システムリソース情報取得

### SSOT API MCP

- `ssot_api_health` - ヘルスチェック
- `ssot_get` - SSOTデータ取得
- `ssot_get_summary` - SSOTサマリー取得
- `ssot_get_services` - サービス状態取得
- `ssot_get_recent_inputs` - 最新指令取得
- `ssot_get_last_error` - 直近エラー取得

### Service Monitor MCP

- `service_monitor_health` - ヘルスチェック
- `service_monitor_get_status` - 監視ステータス取得

---

## 🔧 環境変数

### Unified API Server

```bash
MANAOS_INTEGRATION_API_URL=http://localhost:9500
COMFYUI_URL=http://localhost:8188
SEARXNG_BASE_URL=http://localhost:8080
OBSIDIAN_VAULT_PATH=/path/to/vault
```

### Step Deep Research Service

```bash
STEP_DEEP_RESEARCH_URL=http://localhost:5121
```

### Gallery API Server

```bash
GALLERY_API_URL=http://localhost:5559
COMFYUI_URL=http://localhost:8188
GALLERY_IMAGES_DIR=/path/to/images
```

---

## 🐳 Docker環境変数

`docker-compose.manaos-services.yml` で設定可能：

```yaml
environment:
  - COMFYUI_URL=http://host.docker.internal:8188
  - SEARXNG_BASE_URL=http://host.docker.internal:8080
  - OBSIDIAN_VAULT_PATH=/app/obsidian_vault
```

---

## 📝 使用例

### Cursorでの使用例

```
ユーザー: ComfyUIで画像を生成して
AI: comfyui_generate_imageツールを使用して画像を生成します
```

```
ユーザー: 「Pythonの最新情報」について深くリサーチして
AI: step_deep_research_createツールでリサーチジョブを作成し、実行します
```

```
ユーザー: 画像を生成して
AI: gallery_generate_imageツールを使用して画像を生成します
```

---

## 🔍 トラブルシューティング

### MCPサーバーが起動しない

1. 依存関係をインストール：
   ```bash
   pip install -r requirements.txt
   ```

2. Pythonパスを確認：
   ```bash
   python --version  # Python 3.11以上が必要
   ```

3. 環境変数を確認：
   ```bash
   echo $MANAOS_INTEGRATION_API_URL
   ```

### Dockerコンテナが起動しない

1. ログを確認：
   ```bash
   docker-compose -f docker-compose.manaos-services.yml logs
   ```

2. ポートの競合を確認：
   ```bash
   netstat -an | grep -E "9500|5121|5559"
   ```

3. ビルドを再実行：
   ```bash
   docker-compose -f docker-compose.manaos-services.yml build --no-cache
   ```

### APIサーバーに接続できない

1. サーバーが起動しているか確認：
   ```bash
   curl http://localhost:9500/health
   ```

2. ファイアウォール設定を確認

3. 環境変数を確認

---

## 📚 参考資料

- [MCP SDK Documentation](https://modelcontextprotocol.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)

---

## ✅ 完了チェックリスト

- [x] Unified API Server MCPサーバー実装
- [x] Step Deep Research Service MCPサーバー実装
- [x] Gallery API Server MCPサーバー実装
- [x] Unified API Server Dockerfile作成
- [x] Step Deep Research Service Dockerfile作成
- [x] Gallery API Server Dockerfile作成
- [x] docker-compose.yml作成
- [x] セットアップガイド作成

---

## 🎉 次のステップ

1. **テスト**: 各MCPサーバーとDockerコンテナをテスト
2. **ドキュメント**: APIドキュメントの作成
3. **最適化**: パフォーマンスの最適化
4. **監視**: ログとメトリクスの設定
