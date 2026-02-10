# Cursor → ManaOS Webhook (PoC)

このファイルは、Cursor（または他サービス）から送られた会話を ManaOS の記憶システムに自動保存するための簡易 Webhook PoC の使い方を示します。

## 起動
VS Code のタスクから起動するか、直接 Python で実行してください。

- VS Code タスク: `ManaOS: Cursor webhook`
- 直接起動:

```bash
python manaos_integrations/cursor_webhook.py
```

デフォルトは `http://127.0.0.1:9700/cursor/webhook` に POST を受け付けます。`CURSOR_WEBHOOK_PORT` 環境変数で変更できます。

## テスト例
ローカルから簡単に動作確認できます。

```bash
curl -X POST http://127.0.0.1:9700/cursor/webhook \
  -H "Content-Type: application/json" \
  -d '{"content":"テストメッセージ","metadata":{"source":"cursor","user":"mana"}}'
```

期待されるレスポンス:

```json
{"ok": true, "memory_id": "..."}
```

## Cursor 側の設定
Cursor 側が外部エンドポイントに POST できる場合は、会話イベントに対して上記エンドポイントへ JSON を投げるように設定してください。

## セキュリティ
この PoC は簡易な認証をサポートします。環境変数 `CURSOR_WEBHOOK_SECRET` を設定してください。

- HMAC方式（推奨）: リクエストにヘッダー `X-Cursor-Signature: sha256=<hex>` を付与し、`sha256` の HMAC-SHA256 を `CURSOR_WEBHOOK_SECRET` で生成して送信します。
- Bearerトークン: `Authorization: Bearer <token>` の `<token>` を `CURSOR_WEBHOOK_SECRET` と一致させる方法もサポートします。

例（HMAC 送信）:

```bash
SECRET=your_secret
BODY='{"content":"テスト","metadata":{"source":"cursor"}}'
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -hex | sed 's/^.* //')
curl -X POST http://127.0.0.1:9700/cursor/webhook \
  -H "Content-Type: application/json" \
  -H "X-Cursor-Signature: sha256=$SIG" \
  -d "$BODY"
```

注意: 本番では HTTPS、署名検証、受信IP制限、リプレイ防止など追加の安全対策を必須にしてください。

## リプレイ防止のテスト
`send_cursor_webhook.py` を使ってタイムスタンプ＋nonce付きのリクエストを送ることができます。例:

```bash
export CURSOR_WEBHOOK_SECRET=your_secret
python manaos_integrations/send_cursor_webhook.py
```

同じ `nonce` を再利用するとサーバーは `replay` エラーを返します。`CURSOR_WEBHOOK_MAX_SKEW` で許容時差（秒）を調整できます（デフォルト300秒）。

## サービス化 (推奨)
開発環境や本番で恒常的に動かす場合、systemd（Linux）または Windows サービスとして登録してください。

Linux (systemd) の例:

1. ファイル `deploy/cursor_webhook.service` を `/etc/systemd/system/` にコピーして、`WorkingDirectory` と `ExecStart` のパスを環境に合わせて修正します。
2. 有効化と起動:

```bash
sudo cp deploy/cursor_webhook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cursor_webhook.service
sudo systemctl start cursor_webhook.service
sudo journalctl -u cursor_webhook.service -f
```

Windows の例（PowerShell）:

1. `deploy/install_cursor_webhook_windows.ps1` を管理者権限で実行し、`-PythonPath` を指定して Python 実行ファイルへのパスを合わせます。

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\deploy\install_cursor_webhook_windows.ps1 -PythonPath "C:\Python311\python.exe"
Get-Service -Name ManaOS_CursorWebhook
```

サービス化の際は、ログの取り方（systemd ジャーナル、Windows イベント、ファイル出力）や TLS/プロキシ（nginx などで HTTPS 終端）を必ず設計してください。

## TLS/Reverse proxy（nginx）
同梱の `deploy/nginx_cursor.conf` は nginx で TLS 終端してローカルの webhook に転送するテンプレートです。証明書パスや `server_name` を環境に合わせて編集してください。

## ログ
Webhook はファイルローテーション付きのログを出力します（デフォルト `manaos_integrations/logs/cursor_webhook.log`）。環境変数 `CURSOR_WEBHOOK_LOG` でログファイル／フォルダを変更できます。ログローテーションは最大 5MB、バックアップ 5 世代です。

## PoC 実行スクリプト
ローカル確認用に次のスクリプトを追加しました:

- `scripts/run_poc.sh` — Unix 系での PoC 実行（一時的に webhook を起動して `send_cursor_webhook.py` を 2 回送信）
- `scripts/run_poc.ps1` — Windows PowerShell 用同等スクリプト

実行例 (Unix):

```bash
export CURSOR_WEBHOOK_SECRET=your_secret
./scripts/run_poc.sh
```

## Let's Encrypt / certbot メモ
nginx で TLS を自動化するには `certbot` を使うのが手軽です。簡易手順:

```bash
# インストール (Debian/Ubuntu 例)
sudo apt update && sudo apt install -y certbot python3-certbot-nginx

# nginx サイト設定を配置 (deploy/nginx_cursor.conf を編集して /etc/nginx/sites-available/cursor)
sudo ln -s /etc/nginx/sites-available/cursor /etc/nginx/sites-enabled/cursor
sudo nginx -t && sudo systemctl reload nginx

# certbot による証明書発行と自動設定
sudo certbot --nginx -d cursor.example.com
```

certbot は自動で nginx 設定を書き換え、証明書の自動更新を cron/systemd タイマーで設定します。運用環境では HTTP → HTTPS リダイレクトや HSTS などの追加設定を検討してください。

## ローカルでの CI / テスト実行
リポジトリに追加した GitHub Actions CI と同等の手順をローカルで実行するには以下を使います。

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
# Lint
python -m pip install flake8
flake8 || true
# Run tests if any
if [ -d tests ] || ls test_*.py 1>/dev/null 2>&1; then
  pytest -q
else
  echo "No tests found"
fi
```

GitHub Actions は `.github/workflows/ci.yml` を用いて、push / pull_request 時に同様のチェックを自動実行します。


## 統合ポイント
- 記憶保存は `manaos_core_api.remember()` を呼び出します。`manaos_core_api` が使用可能であることを前提とします。
- 追加で Webhook 認証、受信フォーマット検証、ログ集約を推奨します。
