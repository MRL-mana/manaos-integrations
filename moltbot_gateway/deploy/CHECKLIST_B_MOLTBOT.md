# B：本物 Moltbot 接続（executor 差し替え）手順

A 完了（200 / 401 / 429 揃い）後に進める。いきなり全部やらず、順番に通す。

> **Moltbot のインストール**: 本物で動かす場合は **OpenClaw（旧 Moltbot）のインストールが別途必要**です。手順は **`deploy/INSTALL_OPENCLAW.md`** を参照。インストール後、`MOLTBOT_DAEMON_URL` と `MOLTBOT_DAEMON_TOKEN`（または `OPENCLAW_GATEWAY_TOKEN`）を設定してください。

---

## 前提

- Gateway は **executor 抽象化済み**（`EXECUTOR=mock|moltbot`）。
- `executor/mock.py` … モック即時実行。
- `executor/moltbot.py` … 本物用。最初は **list_files / file_read のみ許可**。他は拒否。

---

## ✅ 1. EXECUTOR を moltbot に切替

- [ ] 環境変数 `EXECUTOR=moltbot` を設定（systemd の `EnvironmentFile` または service の `Environment`）
- [ ] Gateway 再起動: `sudo systemctl restart moltbot-gateway`
- [ ] 本物未設定のままなら **mock にフォールバック**して動く（list_files だけ許可、他は rejected）

---

## ✅ 2. 本物接続の設定（推奨: OpenClaw Tools Invoke）

- [ ] **OpenClaw Gateway**: `MOLTBOT_DAEMON_URL=http://127.0.0.1:18789` を設定（`openclaw status` でポート確認）
- [ ] **認証**: `MOLTBOT_DAEMON_TOKEN` または `OPENCLAW_GATEWAY_TOKEN` に OpenClaw の Gateway トークンを設定
- [ ] 代替: **CLI 利用**: `MOLTBOT_CLI_PATH=/path/to/openclaw` を設定（`openclaw run --plan '...'` 相当のサポートがある場合）

未設定のままなら `moltbot.py` は **mock にフォールバック**（execute_events は流れる）。詳細は `deploy/INSTALL_OPENCLAW.md`。

---

## ✅ 3. 最初は list_files だけ通す

- [ ] **list_files だけ**の Plan を送って、`execute_events` が `result` と `moltbot_audit/.../execute.jsonl` に流れることを確認
- [ ] まなOS 母艦で: `python manaos_moltbot_runner.py list_only` を実行（path はデフォルト `~/Downloads`、第2引数で変更可）
- [ ] Phase1 プラン（list_files → classify → move）を送ると、`EXECUTOR=moltbot` では move が許可外のため `success: false`, `status: rejected` になる想定

---

## ✅ 4. execute.jsonl のイベント確認

- [ ] `moltbot_audit/YYYY-MM-DD/plan-xxx/execute.jsonl` を開く
- [ ] 1 行 1 イベントで `step_id`, `event`, `tool` が入っていることを確認

---

## ✅ 5. file_move 等を解放する場合

- [ ] `executor/moltbot.py` の `ALLOWED_ACTIONS_MOLTBOT` に `move_files` 等を追加
- [ ] `ACTION_TO_SKILL` にマッピングが入っていることを確認
- [ ] 本物 daemon/CLI 側で該当 skill を実装してから解放すること

---

## PlanStep → skill マッピング（Gateway 側で固定）

| Plan action   | マッピング先（例）   |
|---------------|----------------------|
| list_files    | exec（dir /b）        |
| file_read     | skills.fs.read        |
| classify_files| skills.classify      |
| move_files    | skills.fs.move       |

まなOS 側は変えず、Gateway だけで吸収する。
