# ManaOS統合サービス セットアップ手順

**作成日**: 2025-01-28  
**状態**: ✅ 完全実装済み

---

## 📋 前提条件

- Docker Desktop（Windows/Mac/Linux）
- Python 3.11以上
- Git

---

## 🚀 クイックセットアップ（5分）

### ステップ1: MCPサーバーの依存関係をインストール

```powershell
# プロジェクトルートで実行
cd C:\Users\mana4\Desktop\manaos_integrations

# すべてのMCPサーバーの依存関係を一括インストール
pip install mcp requests
```

### ステップ2: Cursor MCP設定を追加

```powershell
# PowerShellで実行
.\add_all_mcp_servers_to_cursor.ps1
```

または手動で `.cursor/mcp.json` に `MCP_CONFIG_TEMPLATE.json` の内容をコピー

### ステップ3: Dockerサービスを起動

```powershell
# すべてのAPIサービスを起動
docker-compose -f docker-compose.manaos-services.yml up -d

# 状態確認
docker-compose -f docker-compose.manaos-services.yml ps
```

### ステップ4: テスト実行

```powershell
# すべてのサービスのヘルスチェック
.\test_all_services.ps1
```

### ステップ5: Cursorを再起動

Cursorを再起動して、MCPサーバーが利用可能か確認してください。

---

## 📋 詳細セットアップ

### 1. MCPサーバーのセットアップ（個別インストール）

```bash
# プロジェクトルートで実行
cd c:\Users\mana4\Desktop\manaos_integrations

# 各MCPサーバーの依存関係をインストール
pip install mcp requests

# または個別にインストール
cd unified_api_mcp_server && pip install -r requirements.txt && cd ..
cd step_deep_research_mcp_server && pip install -r requirements.txt && cd ..
cd gallery_api_mcp_server && pip install -r requirements.txt && cd ..
cd system_status_mcp_server && pip install -r requirements.txt && cd ..
cd ssot_mcp_server && pip install -r requirements.txt && cd ..
cd service_monitor_mcp_server && pip install -r requirements.txt && cd ..
cd web_voice_mcp_server && pip install -r requirements.txt && cd ..
cd portal_integration_mcp_server && pip install -r requirements.txt && cd ..
cd slack_integration_mcp_server && pip install -r requirements.txt && cd ..
cd portal_voice_integration_mcp_server && pip install -r requirements.txt && cd ..
```

### 2. Cursor MCP設定（手動）

`.cursor/mcp.json` に `MCP_CONFIG_TEMPLATE.json` の内容をコピーして追加してください。

または、既存の設定に以下を追加：

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
    },
    "web-voice": {
      "command": "python",
      "args": ["-m", "web_voice_mcp_server.server"],
      "env": {
        "WEB_VOICE_API_URL": "http://localhost:5115"
      }
    },
    "portal-integration": {
      "command": "python",
      "args": ["-m", "portal_integration_mcp_server.server"],
      "env": {
        "PORTAL_API_URL": "http://localhost:5108"
      }
    },
    "slack-integration": {
      "command": "python",
      "args": ["-m", "slack_integration_mcp_server.server"],
      "env": {
        "SLACK_API_URL": "http://localhost:5114"
      }
    },
    "portal-voice-integration": {
      "command": "python",
      "args": ["-m", "portal_voice_integration_mcp_server.server"],
      "env": {
        "PORTAL_VOICE_API_URL": "http://localhost:5116"
      }
    }
  }
}
```

### 3. Docker Composeでサービスを起動

```bash
# すべてのAPIサービスを起動
docker-compose -f docker-compose.manaos-services.yml up -d

# AIサービスも起動（オプション）
docker-compose -f docker-compose.ai-services.yml up -d

# すべてを一度に起動
docker-compose -f docker-compose.manaos-services.yml -f docker-compose.ai-services.yml up -d
```

### 4. サービス状態の確認

```bash
# コンテナの状態確認
docker-compose -f docker-compose.manaos-services.yml ps

# ログ確認
docker-compose -f docker-compose.manaos-services.yml logs -f

# 個別サービスのログ
docker-compose -f docker-compose.manaos-services.yml logs -f unified-api
```

---

## 🧪 テスト手順

### MCPサーバーのテスト

```bash
# 各MCPサーバーを個別にテスト
python -m unified_api_mcp_server.server
python -m step_deep_research_mcp_server.server
python -m gallery_api_mcp_server.server
# ... など
```

### APIサービスのテスト

```bash
# ヘルスチェック
curl http://localhost:9500/health  # Unified API
curl http://localhost:5121/health  # Step Deep Research
curl http://localhost:5559/health  # Gallery API
curl http://localhost:5112/health  # System Status
curl http://localhost:5120/health  # SSOT API
curl http://localhost:5111/health  # Service Monitor
curl http://localhost:5115/health  # Web Voice
curl http://localhost:5108/health  # Portal Integration
curl http://localhost:5114/health  # Slack Integration
curl http://localhost:5116/health  # Portal Voice Integration
curl http://localhost:9501/api/llm/health  # LLM Routing API
```

---

## 📚 詳細ドキュメント

- **完全ガイド**: `CONTAINERIZATION_SUMMARY.md`
- **MCPサーバー化**: `MCP_CONTAINERIZATION_SETUP.md`
- **AIサービス**: `AI_SERVICES_CONTAINERIZATION.md`
- **Web系サービス**: `WEB_SERVICES_COMPLETE.md`
- **追加サービス**: `ADDITIONAL_SERVICES_COMPLETE.md`

---

## 🔧 トラブルシューティング

### MCPサーバーが起動しない

1. Pythonパスを確認: `python --version`
2. 依存関係を確認: `pip list | grep mcp`
3. 環境変数を確認: API URLが正しいか

### Dockerコンテナが起動しない

1. Docker Desktopが起動しているか確認
2. ポートが使用中でないか確認: `netstat -an | findstr :9500`
3. ログを確認: `docker-compose logs <service-name>`

### サービス間の通信エラー

1. ネットワークを確認: `docker network ls`
2. 環境変数のURLを確認（`host.docker.internal`を使用）
3. ファイアウォール設定を確認

---

## ✅ 完了チェックリスト

- [ ] MCPサーバーの依存関係インストール
- [ ] Cursor MCP設定ファイル更新
- [ ] Docker Composeでサービス起動
- [ ] 各サービスのヘルスチェック成功
- [ ] MCPサーバーの動作確認
- [ ] サービス間の連携確認

---

## 🎉 次のステップ

1. **統合テスト**: すべてのサービスを連携してテスト
2. **パフォーマンス**: リソース使用量の監視
3. **最適化**: 必要に応じて設定を調整
4. **監視**: ログとメトリクスの設定
