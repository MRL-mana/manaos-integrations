# Pixel7 5分セキュア導線（漏えい防止つき）

この手順は、ManaOS の Pixel7 連携を **安全デフォルト** で運用するための最小セットです。

## 先に結論（漏えいする？）

- デフォルト設定のままなら、Pixel7 API は **トークン必須 + Tailscaleクライアント限定** です。
- さらに `PIXEL7_API_PROFILE=core` では、端末操作系APIを閉じます。
- ただし、以下を自分で有効化した場合は外部送信が発生します。
  - 外部LLM API（OpenAI 等）
  - Slack/Discord 等の通知連携
  - ngrok 等の公開トンネル

## 0. 必須環境変数（Pixel7 / Termux）

```bash
export PIXEL7_API_TOKEN='十分長いランダム文字列'
export PIXEL7_API_PROFILE='core'
# 既定で有効だが明示推奨
export PIXEL7_API_TAILSCALE_ONLY='1'
```

## 1. 起動

```bash
python pixel7_api_gateway.py
```

## 2. 母艦から疎通確認

```powershell
python scripts/pixel7/manaos_pixel7_cli.py --base http://127.0.0.1:5122 health
python scripts/pixel7/manaos_pixel7_cli.py --base http://127.0.0.1:5122 status --token $env:PIXEL7_API_TOKEN
```

## 3. 操作系APIを使うときだけ一時的に解放

```bash
export PIXEL7_API_PROFILE='full'
```

利用後は戻す:

```bash
export PIXEL7_API_PROFILE='core'
```

補足: `pixel7_control_auto.ps1` / `pixel7_macro_send_auto.ps1` の `HTTPFirst` は、
`api_profile` が `full` でない場合に **自動でADB優先** に切り替わります（安全側）。

## 4. 最小CLI

- `health` : `/health`（認証不要）
- `status` : `/api/status`（認証必須）
- `open-url` : `/api/open/url`（`full` プロファイル必須）

例:

```powershell
python scripts/pixel7/manaos_pixel7_cli.py --base http://127.0.0.1:5122 open-url https://moeru.ai --token $env:PIXEL7_API_TOKEN
```

## 4.5 プロファイルガード（推奨）

実行前に profile を明示確認できます。

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\pixel7_check_api_profile.ps1 -Require any
pwsh -NoProfile -ExecutionPolicy Bypass -File .\pixel7_check_api_profile.ps1 -Require core
pwsh -NoProfile -ExecutionPolicy Bypass -File .\pixel7_check_api_profile.ps1 -Require full
```

VS Code タスクも追加済み:

- `ManaOS: Pixel7 API Profile Check`
- `ManaOS: Pixel7 API Guard (Require core)`
- `ManaOS: Pixel7 API Guard (Require full)`

## 5. 秘密情報の扱い

- Git管理対象に以下を入れない:
  - `.env`
  - `.pixel7_api_token.txt`
  - `token.json` / `credentials.json`
- ログ共有時はトークン・内部IPをマスクする。

## 6. 追加で安全にするなら

- Unified API 側の3段階キー（Admin/Ops/Read-only）を有効化
- 公開する場合は必ずリバースプロキシ + IP制限
- `PIXEL7_API_PROFILE=full` 常時運用は避ける

---

この導線は「まず漏えいしない運用」を優先しています。機能拡張は `core` で安定運用できてから段階的に有効化してください。
