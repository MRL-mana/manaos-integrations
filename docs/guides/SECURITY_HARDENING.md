## 目的

ManaOS統合API（`unified_api_server.py`）を **事故りにくく** 運用するための最小ハードニング手順。

## 推奨: 3段階キー（Admin / Ops / Read-only）

- **Admin**: `MANAOS_INTEGRATION_API_KEY`（全アクセス）
- **Ops**: `MANAOS_INTEGRATION_OPS_API_KEY`（POST/PUT/DELETE + 危険GET）
- **Read-only**: `MANAOS_INTEGRATION_READONLY_API_KEY`（許可されたGET/HEADのみ）

クライアントは以下いずれかで送ります:

- `X-API-Key: <key>`
- `Authorization: Bearer <key>`

## パスのスコープ判定（運用で調整可能）

- **Read-only許可**: `MANAOS_READONLY_PATH_PREFIXES`（CSV）
  - 例: `/health,/ready,/status,/openapi.json,/api/integrations/status`
- **GETでもOps扱い**: `MANAOS_SENSITIVE_PATH_PREFIXES`（CSV）
  - 例: `/emergency,/api/emergency,/api/system/docker`

- **Admin専用（最重要）**: `MANAOS_ADMIN_ONLY_PATH_PREFIXES`（CSV）
  - 例: `/emergency,/api/emergency,/api/system/docker,/api/llm,/api/memory,/api/google_drive,/api/rows,/api/n8n,/api/civitai,/api/voice,/api/slack`
  - これらは **Opsキーではアクセス不可**（Adminキーのみ）

デフォルトは「ほとんどのGETもOps必須」に寄せてあります（安全側）。

補足:
- `/status` と `/api/integrations/status` は、read-onlyキーでアクセスした場合 **情報を最小化**します（環境変数名や内部詳細を返しません）。

## IP制御（推奨）

- `MANAOS_IP_ALLOWLIST`（CSV、空なら無効）
- `MANAOS_IP_BLOCKLIST`（CSV、allowlistより先にブロック）

例:

```env
MANAOS_IP_ALLOWLIST=127.0.0.1,10.0.0.10
MANAOS_IP_BLOCKLIST=
```

## もっとも安全な起動（ローカル専用）

```env
MANAOS_INTEGRATION_HOST=127.0.0.1
MANAOS_DEBUG=false
```

この場合、キー未設定でも localhost からのみアクセスできます（デフォルト挙動）。

## 本番起動（推奨: Waitress）

Flask開発サーバ（`python unified_api_server.py`）ではなく、Waitressで起動します。

- `run_unified_api_server_prod.py`（本番WSGI起動）
- `start_unified_api_server_prod.bat`（Windows向け）

例:

```bat
start_unified_api_server_prod.bat
```

## Windowsサービス化（任意: NSSM）

Windowsで常時稼働したい場合、NSSMでサービス化できます。

- インストール: `scripts/windows/install_unified_api_service.ps1`
- アンインストール: `scripts/windows/uninstall_unified_api_service.ps1`

## リバースプロキシ（Nginx）運用の注意

### 原則

- **アプリは localhost にのみバインド**
- 外部公開は Nginx 側で実施（Basic認証やIP制限、TLS終端）

### Nginx例（概念）

```nginx
server {
  listen 443 ssl;
  server_name example.com;

  # 追加の防御（例）
  auth_basic "Restricted";
  auth_basic_user_file /etc/nginx/.htpasswd;

  location / {
    proxy_pass http://127.0.0.1:9502;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

このリポジトリにはサンプル設定として `docs/guides/NGINX_REVERSE_PROXY_EXAMPLE.conf` も同梱しています。

## 監査ログ（推奨）

統合APIは、秘密情報を含めない最小監査ログを出せます。

- `MANAOS_AUDIT_LOG=true|false`
- `MANAOS_AUDIT_LOG_FORMAT=json|text`
- `MANAOS_AUDIT_LOG_FILE`（未設定なら `<repo>/logs/audit/manaos_audit_{date}.jsonl` に追記。指定するとそのファイルに追記）
- `MANAOS_AUDIT_LOG_MAX_BYTES`（サイズでローテーション、0で無効）
- `MANAOS_AUDIT_LOG_BACKUPS`（保持世代数）
（監査ログには `latency_ms` も含まれます）
（`request_id` と `user_agent` も含まれます。レスポンスヘッダ `X-Request-Id` にも同じIDを返します）

補足:
- `MANAOS_AUDIT_LOG_FILE` には `{date}`（YYYYMMDD）を含められます。
  - 例: `C:\\logs\\manaos_audit_{date}.jsonl`

## OpenAPIの公開制御

- `MANAOS_EXPOSE_OPENAPI=true|false`
  - `false` の場合 `/openapi.json` は 404 を返します（エンドポイント一覧の露出を避けたいとき）。

### `X-Forwarded-For` を使う場合

アプリ側は **デフォルトで `X-Forwarded-For` を信用しません**。  
信頼できるリバプロ配下に置くときだけ:

```env
MANAOS_TRUST_X_FORWARDED_FOR=true
```

※公開インターネットに直結したまま `true` にすると、IP偽装が成立し得るので注意。

## セキュリティヘッダ（推奨）

- `MANAOS_SECURITY_HEADERS=true|false`
  - `true` の場合、`X-Content-Type-Options` / `X-Frame-Options` など最小限のヘッダを付与します。

## レート制限 / 同時実行制限（推奨）

重いエンドポイントに対する事故（連打/DoS/二重実行）を抑えるための簡易ガードです（プロセス内・ベストエフォート）。

- `MANAOS_RATE_LIMIT_ENABLED=true|false`
- `MANAOS_RATE_LIMIT_WINDOW_SECONDS`（デフォ: 60）
- `MANAOS_RATE_LIMIT_RPM`（デフォ: 60）
- `MANAOS_RATE_LIMIT_RULES`（例: `/api/llm=20,/api/system/docker=10`）

- `MANAOS_CONCURRENCY_ENABLED=true|false`
- `MANAOS_CONCURRENCY_LIMITS`（例: `/api/llm=2,/api/system/docker=1`）

## 二重ロック（Confirm Token / 推奨）

緊急系・システム操作系に「キー + 追加トークン」を要求できます（事故防止）。

- `MANAOS_CONFIRM_TOKEN`（設定した場合のみ有効）
- `MANAOS_CONFIRM_TOKEN_PATH_PREFIXES`（CSV）
  - デフォルト: `/api/emergency,/api/system/docker`

該当パスにアクセスする時はヘッダを追加します:

- `X-Confirm-Token: <token>`

### 時限HMAC方式（おすすめ）

`MANAOS_CONFIRM_TOKEN_SECRET` を設定すると **時限HMAC方式**になります（固定トークンより安全）。

- `MANAOS_CONFIRM_TOKEN_SECRET`（設定した場合はこの方式が優先）
- `MANAOS_CONFIRM_TOKEN_PERIOD_SECONDS`（デフォルト: 30）
- `MANAOS_CONFIRM_TOKEN_ACCEPT_PREVIOUS`（デフォルト: true。時計ズレ対策）

追加オプション:
- `MANAOS_CONFIRM_TOKEN_BIND_PATH=true|false`
  - `true` の場合、トークン生成に **保護対象のパスprefix** も混ぜます（使い回し耐性が上がります）

クライアントは以下で `X-Confirm-Token` を作ります:

- `token = HMAC_SHA256_HEX(secret, floor(unix_time / period_seconds))`

`MANAOS_CONFIRM_TOKEN_BIND_PATH=true` の場合は:

- `scope = マッチした保護prefix（例: /api/system/docker）`
- `token = HMAC_SHA256_HEX(secret, floor(unix_time / period_seconds) + ":" + scope)`

（監査ログには `confirm_required / confirm_ok / confirm_mode` が入ります）

## CIのシークレットスキャン（参考）

GitHub ActionsのCIでは gitleaks が動く前提です。設定は `.gitleaks.toml` を参照します。


