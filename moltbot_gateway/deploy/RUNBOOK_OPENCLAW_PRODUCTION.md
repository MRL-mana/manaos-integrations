# OpenClaw インストール ＋ 本物で本格運用（手順）

母艦で OpenClaw をインストールし、まなOS Gateway を本物モードで常駐させる手順。**自分の PowerShell で実行**してください（Cursor 内のターミナルでは npm のキャッシュ制限でインストールが失敗する場合があります）。

---

## 前提

- **Node >= 22** 推奨（v20 でも動く場合あり）。`node -v` で確認。
- Windows の場合は **PowerShell** を管理者でなくても可。WSL2 の場合は bash で同様の手順。

---

## 1. OpenClaw をインストール

### Windows（PowerShell）

**自分の PowerShell を開き**、次を実行:

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

オンボーディングをスキップしてインストールだけする場合:

```powershell
$env:OPENCLAW_NO_ONBOARD = "1"
iwr -useb https://openclaw.ai/install.ps1 | iex
```

### 手動（npm のみ）

```powershell
npm install -g openclaw@latest
```

---

## 2. OpenClaw の daemon を入れる（初回）

インストール後、daemon（Gateway）を有効にする:

```powershell
openclaw onboard --install-daemon
```

---

## 3. 動作確認

```powershell
openclaw doctor
openclaw status
openclaw health
```

Gateway が起動していれば、ポート（多くは **18789**）が表示されます。この URL を次のステップで使います。

---

## 4. 本物運用用の環境ファイルを作る

リポジトリの `moltbot_gateway\deploy\` に、本物接続用の環境変数ファイルを作成します。

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
copy moltbot_gateway\deploy\gateway_production.env.example moltbot_gateway\deploy\gateway_production.env
notepad moltbot_gateway\deploy\gateway_production.env
```

`gateway_production.env` を編集:

- **MOLTBOT_DAEMON_URL**: OpenClaw Gateway の URL（例: `http://127.0.0.1:18789`）。`openclaw status` のポートに合わせる。
- **MOLTBOT_DAEMON_TOKEN**: OpenClaw の Gateway 認証トークン。OpenClaw の設定（`~/.openclaw` や `gateway.auth.token`）で確認するか、[Gateway 認証](https://docs.molt.bot/gateway/authentication) を参照。

例:

```env
EXECUTOR=moltbot
MOLTBOT_DAEMON_URL=http://127.0.0.1:18789
MOLTBOT_DAEMON_TOKEN=あなたのトークン
```

---

## 5. Gateway を常駐させる（本物モードで）

リポジトリルートで:

```powershell
.\moltbot_gateway\deploy\register_gateway_autostart.ps1
```

→ ログオン時に **run_gateway_wrapper_production.ps1** が実行されます。
**gateway_production.env** があると本物（EXECUTOR=moltbot）で起動し、ないとモックで起動します。

いま 1 回だけ起動して試す場合:

```powershell
.\moltbot_gateway\deploy\run_gateway_wrapper_production.ps1
```

（別ウィンドウで）OpenClaw の daemon が動いていること、および `gateway_production.env` に URL・トークンを書いたことを確認してください。

---

## 6. 動作確認（list_only）

Gateway が起動している状態で:

```powershell
python manaos_moltbot_runner.py list_only
```

→ `moltbot_audit/YYYY-MM-DD/plan-xxx/` に監査が増え、本物の OpenClaw Tools Invoke が呼ばれていれば成功です。
404 や 401 の場合は、OpenClaw 側のツール許可・トークン・URL を確認してください。

---

## 6.1 OpenClaw Gateway を「サービス無し」で常駐させる（Windows向け代替）

`openclaw onboard --install-daemon` が権限で失敗する場合は、OpenClaw 側の常駐を **タスクスケジューラ**で代替できます。

1. `gateway_production.env` を作成済み（`MOLTBOT_DAEMON_URL` と `MOLTBOT_DAEMON_TOKEN` を設定済み）にする
2. リポジトリルートで次を実行:

```powershell
.\moltbot_gateway\deploy\register_openclaw_gateway_autostart.ps1
```

このタスクは `run_openclaw_gateway_production.ps1` をログオン時に起動し、`MOLTBOT_DAEMON_URL` のポートで OpenClaw Gateway を待ち受けます。

手動で 1 回だけ起動するなら:

```powershell
.\moltbot_gateway\deploy\run_openclaw_gateway_production.ps1
```

疎通（/tools/invoke）を確認するなら:

```powershell
.\moltbot_gateway\deploy\check_openclaw_tools_invoke.ps1
```

---

## 7. 本番運用チェックリスト

- [ ] OpenClaw インストール済み（`openclaw status` で Gateway 起動確認）
- [ ] `gateway_production.env` に MOLTBOT_DAEMON_URL / MOLTBOT_DAEMON_TOKEN を設定
- [ ] タスク「MoltbotGateway」で常駐（または手動で run_gateway_wrapper_production.ps1）
- [ ] `.env` に MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088 と MOLTBOT_GATEWAY_SECRET を設定
- [ ] 監査ローテ: `.\moltbot_gateway\deploy\register_audit_rotate_monthly.ps1`（任意）

詳細は **CHECKLIST_PRODUCTION.md** と **INSTALL_OPENCLAW.md**。

---

## トラブル

- **openclaw が見つからない**: Node のグローバル bin が PATH に入っているか確認。`npm prefix -g` の `bin` を PATH に追加。
- **Gateway が 404/401**: OpenClaw の gateway.auth と MOLTBOT_DAEMON_TOKEN が一致しているか、ツールが許可されているか確認。
- **Node が古い**: OpenClaw は Node >= 22 推奨。`nvm install 22` などでアップグレード。

### Gateway サービスが入れない・Gateway not running のとき

**現象**: `openclaw doctor` で「Gateway service update failed」「Gateway service install failed」や「schtasks create failed」（アクセスが拒否されました）、`openclaw status` で「Gateway not running」「unreachable (ECONNREFUSED 127.0.0.1:18789)」と出る。

**対処 A（推奨）: 管理者 PowerShell でサービスを入れる**

1. **PowerShell を管理者として実行**（スタート → 「PowerShell」→ 右クリック → 管理者として実行）。
2. 次を実行して Gateway サービスを入れ直す:
   ```powershell
   openclaw doctor
   ```
   「Update gateway service config」「Install gateway service now?」は **Yes** を選ぶ。
3. 完了後、`openclaw status` で Gateway が running になっているか確認。

**対処 B: サービスを使わず、手動で Gateway を起動する**

1. **1 つ目の PowerShell**（通常の権限でよい）で、Gateway をフォアグラウンドで起動:
   ```powershell
   openclaw gateway
   ```
   または `openclaw gateway run`。ポート 18789 で待ち受けるまでそのウィンドウは閉じない。
2. **2 つ目の PowerShell** でリポジトリに移動し、まなOS Gateway と runner を実行:
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   .\moltbot_gateway\deploy\run_gateway_wrapper_production.ps1
   ```
   別ウィンドウで:
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   python manaos_moltbot_runner.py list_only
   ```

- **run_gateway_wrapper_production.ps1 が見つからない**: 必ず **リポジトリのルート**（`manaos_integrations`）に移動してから実行する。例: `cd C:\Users\mana4\Desktop\manaos_integrations` のあと `.\moltbot_gateway\deploy\run_gateway_wrapper_production.ps1`。
