# 本番運用スタート（今すぐやること）

母艦だけで本番運用を開始する最小手順。上から順にやる。

- **本物 OpenClaw で本格運用**したい場合は **`RUNBOOK_OPENCLAW_PRODUCTION.md`** に従い、OpenClaw をインストール → `gateway_production.env` を作成 → 常駐登録（同じ `register_gateway_autostart.ps1` で本物モードになる）。

---

## 1. Gateway を常駐させる（1回だけ）

リポジトリルートで:

```powershell
.\moltbot_gateway\deploy\register_gateway_autostart.ps1
```

→ ログオン時に **run_gateway_wrapper_production.ps1** が実行され、Gateway が自動起動する。
**gateway_production.env** があると本物 OpenClaw に接続し、ないとモックで起動する。
いま起動したいだけなら（本物モードの場合は先に `gateway_production.env` を作成）:

```powershell
.\moltbot_gateway\deploy\run_gateway_wrapper_production.ps1
```

または Gateway 起動 + list_only 1回:

```powershell
.\moltbot_gateway\deploy\start_gateway_and_run_list_only.ps1
```
（常駐はしない）

---

## 2. .env を本番用にしておく

リポジトリルートの `.env` に:

```env
MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088
MOLTBOT_GATEWAY_SECRET=ここに本番用の秘密文字列
```

`register_gateway_autostart.ps1` で作った `run_gateway_wrapper.ps1` の SECRET を同じ値にしたい場合は、`moltbot_gateway\deploy\run_gateway_wrapper.ps1` を開いて `MOLTBOT_GATEWAY_SECRET` を書き換える。

---

## 3. 1回だけ runner で試す

Gateway が起動している状態で:

```powershell
python manaos_moltbot_runner.py list_only
```

→ `moltbot_audit/YYYY-MM-DD/plan-xxx/` に監査が増えればOK。

本物 OpenClaw を使う場合は、先に OpenClaw Gateway が起動していることを確認:

```powershell
.\moltbot_gateway\deploy\check_openclaw_tools_invoke.ps1
```

---

## 4. 監査ローテを月1で回す（任意）

古い監査をためないために、月1回ローテを実行するタスクを登録する:

```powershell
.\moltbot_gateway\deploy\register_audit_rotate_monthly.ps1
```

→ 毎日 0:00 に `rotate_audit.py` が実行され、30日より古い監査が `moltbot_audit/archive/` に移動する。

---

## 5. 本番運用チェックリストを押さえる

- [ ] 常駐: タスク「MoltbotGateway」が有効
- [ ] .env: MOLTBOT_GATEWAY_URL / SECRET が本番値
- [ ] 監査ローテ: 月1回 or 手動で `rotate_audit.ps1`
- [ ] SECRET ローテ: 年1回やることをカレンダーにメモ

詳細は **`CHECKLIST_PRODUCTION.md`**。

---

## トラブル時

- **Gateway が動いていない**: タスクマネージャーで `python` / `uvicorn` を確認。手動で `start_gateway_and_run_list_only.ps1` の起動部分だけ実行して起動確認。
- **runner が Submit failed**: MOLTBOT_GATEWAY_URL が 127.0.0.1:8088 か、Gateway が起動しているか確認。
- **本物 OpenClaw で本格運用**: `RUNBOOK_OPENCLAW_PRODUCTION.md` に従い、OpenClaw インストール → `gateway_production.env` 作成 → 常駐。`CHECKLIST_B_MOLTBOT.md` と `CHECKLIST_PRODUCTION.md` も参照。

以上で本番運用開始。

---

## 本格運用できてる？ 確認コマンド（1分でチェック）

次のコマンドを**リポジトリルート**で実行し、すべて通れば本格運用はできている。

```powershell
# 1) まなOS Gateway (8088) が生きているか
Invoke-WebRequest -Uri http://127.0.0.1:8088/moltbot/health -UseBasicParsing | Select-Object StatusCode
# → StatusCode 200 なら OK

# 2) OpenClaw Gateway (18789) の疎通（本物運用時のみ。gateway_production.env 必須）
.\moltbot_gateway\deploy\check_openclaw_tools_invoke.ps1
# → sessions_list が 200、exec が 200 または 404（警告）なら疎通 OK。404 でも list_files / file_read はローカルフォールバックで動く

# 3) list_only で監査が増えるか（Gateway 起動中に実行）
python manaos_moltbot_runner.py list_only
# → moltbot_audit\YYYY-MM-DD\plan-xxx\ が増えれば OK
```

- **読み取り運用（list_files / file_read）**: 上記が通れば本格運用可能。OpenClaw の exec が 404 でもローカルフォールバックで動作する。
- **書き込み（move_files 等）**: 未解放。必要なら `ALLOWED_ACTIONS_MOLTBOT` と OpenClaw 側のツール許可を拡張する。
