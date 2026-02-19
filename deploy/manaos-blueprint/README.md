# ManaOS Blueprint Stack

このディレクトリは、`chat / code / api` の3入口分離と `DMZ / internal` 分離を一気に導入するための最小構成です。

## 構成

- `chat.<BASE_DOMAIN>` -> Open WebUI
- `code.<BASE_DOMAIN>` -> code-server
- `api.<BASE_DOMAIN>` -> ManaOS API

内部ネットワーク (`internal`) には以下を配置します。

- `manaos-api`
- `qdrant` (vector memory)
- `postgres` (memory metadata)
- `redis` (ops queue/cache)
- `runner` (executor placeholder)

## 起動手順

1. 環境変数ファイルを作成

```powershell
cd deploy/manaos-blueprint
Copy-Item .env.example .env
```

2. `.env` のシークレット値を更新

- `WEBUI_SECRET_KEY`
- `CODE_SERVER_PASSWORD`
- `POSTGRES_PASSWORD`
- `OPS_EXEC_BEARER_TOKEN`

3. スタック起動

```powershell
docker compose -f docker-compose.blueprint.yml --env-file .env up -d --build
```

4. ヘルス確認

```powershell
docker compose -f docker-compose.blueprint.yml ps
```

## Open WebUI 連携（Tool化）

Open WebUI の Tool から `api.<BASE_DOMAIN>` 配下を呼びます。

- `POST /memory/search`
- `POST /memory/write`
- `POST /ops/plan`
- `POST /ops/exec`
- `POST /dev/patch`
- `POST /dev/test`
- `POST /dev/deploy`

## 実運用前チェック

- `api.<BASE_DOMAIN>` の `/ops/exec` と `/dev/deploy` は Bearer + 承認必須
- Reverse proxy 以外のポートは外部公開しない
- Memoryの正史は ManaOS API 側へ一本化

### `/ops/exec` の挙動

- デフォルトは `dry_run=true`（実コマンドは実行しない）
- `OPS_APPROVAL_MODE=required` の場合、`approved=true` が必須
- `OPS_EXEC_BEARER_TOKEN` を設定している場合、`Authorization: Bearer <token>` が必須

## 既存構成との関係

- 既存 `docker-compose.always-ready-llm.yml` はそのまま併用可能
- 本構成は「分離導線の基盤」を作る追加スタックです
