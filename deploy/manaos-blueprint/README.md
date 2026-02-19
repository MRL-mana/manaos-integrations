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

1. `.env` のシークレット値を更新

- `WEBUI_SECRET_KEY`
- `CODE_SERVER_PASSWORD`
- `POSTGRES_PASSWORD`
- `OPS_EXEC_BEARER_TOKEN`

1. スタック起動

```powershell
docker compose -f docker-compose.blueprint.yml --env-file .env up -d --build
```

1. ヘルス確認

```powershell
docker compose -f docker-compose.blueprint.yml ps
```

### ローカル検証モード（DNS未設定環境）

このblueprintはローカル起動時にCaddyをHTTPモードで動かします。

```powershell
$base = "mrl-mana.com"  # .env の BASE_DOMAIN
curl -H "Host: api.$base" http://localhost/health
curl -H "Host: chat.$base" http://localhost/
curl -H "Host: code.$base" http://localhost/
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

### Open WebUI Tool 自動登録

`manaos_blueprint_gateway` ツールをOpen WebUIへ自動登録/更新できます。

```powershell
cd deploy/manaos-blueprint

# 1) 初回だけ signup を一時有効化
$env:ENABLE_SIGNUP = "true"
docker compose -f docker-compose.blueprint.yml --env-file .env up -d --force-recreate open-webui

# 2) ツール登録（既存なら更新）
python bootstrap_openwebui_tools.py --base-domain mrl-mana.com --signup

# 3) signup を元に戻す
Remove-Item Env:ENABLE_SIGNUP -ErrorAction SilentlyContinue
docker compose -f docker-compose.blueprint.yml --env-file .env up -d --force-recreate open-webui
```

登録後は Open WebUI の Workspace > Tools で `ManaOS Blueprint Gateway` を確認できます。

### 自動受け入れテスト

blueprint全体（ingress / API / Open WebUIツール登録）を一括検証します。

```powershell
cd deploy/manaos-blueprint
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_blueprint_acceptance.ps1
```

起動を同時に行う場合:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_blueprint_acceptance.ps1 -StartIfNeeded
```

### ワンコマンド・フルパイプライン

Toolブートストラップ + 受け入れ検証を連続実行します。

```powershell
cd deploy/manaos-blueprint
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_blueprint_full_pipeline.ps1 -StartIfNeeded
```

初回ユーザー未作成の環境では `-BootstrapSignup` を付けます。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_blueprint_full_pipeline.ps1 -StartIfNeeded -BootstrapSignup
```

### 日次自動実行タスク登録

Windowsタスクスケジューラに日次実行を登録します。

```powershell
cd deploy/manaos-blueprint
powershell -NoProfile -ExecutionPolicy Bypass -File .\register_blueprint_acceptance_daily_task.ps1 -StartTime "07:30"
```

失敗時Webhook通知（成功時は任意）を使う場合:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\register_blueprint_acceptance_daily_task.ps1 -StartTime "07:30" -WebhookUrl "https://example-webhook" -WebhookFormat "discord" -NotifyOnSuccess
```

この登録スクリプトは、通知オプションをユーザー環境変数（`MANAOS_WEBHOOK_*`）に保存し、タスク本体のコマンド長を短く保ちます。

`run_blueprint_full_pipeline.ps1` は以下の環境変数も参照します（未指定時のフォールバック）。

- `MANAOS_WEBHOOK_URL`
- `MANAOS_WEBHOOK_FORMAT` (`generic` / `slack` / `discord`)
- `MANAOS_WEBHOOK_MENTION`
- `MANAOS_NOTIFY_ON_SUCCESS` (`true/false`)

Webhook URL が設定されている場合、失敗通知は常時送信されます。成功通知は `-NotifyOnSuccess` または `MANAOS_NOTIFY_ON_SUCCESS=true` で有効化できます。

### 失敗時のみ通知プリセット（ワンコマンド）

日次タスク登録 + 失敗通知設定を一括で行います（成功通知は無効化）。

```powershell
cd deploy/manaos-blueprint
powershell -NoProfile -ExecutionPolicy Bypass -File .\enable_blueprint_failure_notify.ps1 -WebhookUrl "https://example-webhook" -WebhookFormat "discord" -StartTime "07:30"
```

## GitHub Actions 自動実行

workflow は [\.github/workflows/blueprint-acceptance.yml](../../.github/workflows/blueprint-acceptance.yml) です。

- トリガー: `workflow_dispatch` / 毎日定時 / `deploy/manaos-blueprint/**` 変更時 push
- 実行内容: `.env` 自動生成 → `run_blueprint_full_pipeline.ps1` 実行 → ログartifact保存

推奨 Secrets（未設定時は開発用デフォルトにフォールバック）:

- `BLUEPRINT_WEBUI_SECRET_KEY`
- `BLUEPRINT_CODE_SERVER_PASSWORD`
- `BLUEPRINT_POSTGRES_PASSWORD`
- `BLUEPRINT_OPS_EXEC_BEARER_TOKEN`
- `MANAOS_BLUEPRINT_WEBHOOK_URL`
- `MANAOS_BLUEPRINT_WEBHOOK_FORMAT`
- `MANAOS_BLUEPRINT_WEBHOOK_MENTION`
- `MANAOS_BLUEPRINT_NOTIFY_ON_SUCCESS`

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
