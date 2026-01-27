# ManaOS Integrations

ManaOS と外部サービス（ComfyUI / Google Drive / CivitAI / n8n / Slack / Voice など）をつなぐ統合リポジトリです。

## 重要（セキュリティ）

- **統合APIサーバー**: `unified_api_server.py`
- **最小ハードニング手順**: `docs/guides/SECURITY_HARDENING.md`
  - 3段階キー（Admin / Ops / Read-only）
  - IP allow/block、CORS制御
  - 監査ログ、Confirm Token、Rate limit / Concurrency
  - OpenAPI公開制御、セキュリティヘッダ

## 起動

### 開発（ローカル）

```bash
python unified_api_server.py
```

### 本番（推奨: Waitress）

```bat
start_unified_api_server_prod.bat
```

## 依存関係

- 最小: `requirements-core.txt`
- 開発: `requirements-dev.txt`
- 全部入り: `requirements.txt`

## MCPサーバー

- MCP本体: `manaos_unified_mcp_server/server.py`
