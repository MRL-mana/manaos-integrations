# OpenClaw（Moltbot）本物インストール手順

本物の Moltbot で動かすには **OpenClaw**（旧 Moltbot、docs.molt.bot）を別途インストールし、Gateway から OpenClaw の Gateway（Tools Invoke API）に接続します。

## 前提

- **Node >= 22**
- macOS / Linux / **Windows は WSL2** 推奨（ネイティブ Windows は要確認）
- このリポジトリ（moltbot_gateway）には OpenClaw 本体は含まれていません

## 1) インストール（推奨: 公式インストーラ）

### Windows（PowerShell）

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

オンボーディングをスキップする場合:

```powershell
# 非対話でインストールのみ
$env:OPENCLAW_NO_ONBOARD = "1"
iwr -useb https://openclaw.ai/install.ps1 | iex
```

### macOS / Linux

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

次に daemon を入れる場合:

```bash
openclaw onboard --install-daemon
```

### 手動（すでに Node がある場合）

```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
```

## 2) 動作確認

```bash
openclaw doctor
openclaw status
openclaw health
```

Gateway が起動していれば、デフォルトでは **ポート 18789** で HTTP/WS が待ち受けます（要確認: `openclaw status` の表示）。

## 3) まなOS Gateway から本物接続するための設定

OpenClaw の **Gateway**（daemon）の URL と、Tools Invoke API 用の認証トークンを設定します。

| 環境変数 | 説明 | 例 |
|----------|------|-----|
| `EXECUTOR` | `moltbot` にすると本物 executor を使用 | `moltbot` |
| `MOLTBOT_DAEMON_URL` | OpenClaw Gateway のベース URL（ポートは openclaw status で確認） | `http://127.0.0.1:18789` |
| `MOLTBOT_DAEMON_TOKEN` または `OPENCLAW_GATEWAY_TOKEN` | Gateway 認証トークン（Bearer）。OpenClaw の `gateway.auth.token` または `OPENCLAW_GATEWAY_TOKEN` と同一 | あなたのトークン |

- OpenClaw 側で `gateway.auth.mode="token"` のときは `gateway.auth.token`（または `OPENCLAW_GATEWAY_TOKEN`）の値をそのまま使う。
- OpenClaw 側で `gateway.auth.mode="password"` のときは `gateway.auth.password`（または `OPENCLAW_GATEWAY_PASSWORD`）を Bearer として送る（要確認: ドキュメントでは password モード時は password を送るとある）。

### 例（PowerShell・母艦で Gateway 常駐する場合）

```powershell
$env:EXECUTOR = "moltbot"
$env:MOLTBOT_DAEMON_URL = "http://127.0.0.1:18789"
$env:MOLTBOT_DAEMON_TOKEN = "あなたのOpenClaw_GATEWAYトークン"
# その後、moltbot_gateway を起動
& python -m uvicorn moltbot_gateway.gateway_app:app --host 127.0.0.1 --port 8088
```

### 例（run_gateway_wrapper.ps1 で本物を使う場合）

`moltbot_gateway\deploy\run_gateway_wrapper.ps1` を開き、次を追加（またはコメント解除）:

```powershell
$env:EXECUTOR = "moltbot"
$env:MOLTBOT_DAEMON_URL = "http://127.0.0.1:18789"
$env:MOLTBOT_DAEMON_TOKEN = "あなたのトークン"
```

## 4) ツール名の対応（list_files / file_read）

Gateway の executor は、Plan の `action` を OpenClaw の **Tools Invoke** の `tool` 名にマッピングしています。

- `list_files` → `exec`（Windows の場合は `dir /b` を `workdir=<path>` で実行して代用）
- `file_read` → `skills.fs.read`

OpenClaw で実際に登録されているツール名が異なる場合は、`moltbot_gateway/executor/moltbot.py` の `ACTION_TO_SKILL` を編集するか、OpenClaw の `openclaw skills` で確認して合わせてください。ツールがポリシーで許可されていないと Tools Invoke は 404 を返します。

> 注意: `list_files` は `exec` を使うため、OpenClaw 側のツールポリシーで `exec` が許可されている必要があります（許可されない場合は 404）。

## 5) 参考リンク

- インストール: https://docs.molt.bot/install
- Tools Invoke API: https://docs.molt.bot/gateway/tools-invoke-http-api
- Gateway 認証: https://docs.molt.bot/gateway/authentication
- OpenClaw（Moltbot）公式: https://openclaw.ai / https://docs.molt.bot
