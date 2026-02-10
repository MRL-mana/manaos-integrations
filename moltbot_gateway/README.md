# Moltbot Gateway（このは側・最小実装）

まなOS → このは の1本ゲート。署名検証 → Plan保存 → モック実行 → Result保存。まず疎通＋監査ループを完成させ、Moltbot本体は後で繋ぐ。

## このは側での起動（最小）

```bash
cd moltbot_gateway  # またはリポジトリルートで PYTHONPATH に . を足す
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi uvicorn

export MOLTBOT_GATEWAY_SECRET="あなたのsecret"
export MOLTBOT_GATEWAY_DATA_DIR="/var/lib/moltbot_gateway"   # ローカル試行なら ./moltbot_gateway_data
uvicorn gateway_app:app --host 0.0.0.0 --port 8088
```

リポジトリルートから起動する場合（まなOS側と同じツリーで試す場合）:

```bash
# リポジトリルートで
pip install fastapi uvicorn
set MOLTBOT_GATEWAY_DATA_DIR=moltbot_gateway_data
uvicorn moltbot_gateway.gateway_app:app --host 0.0.0.0 --port 8088
```

## まなOS側 .env（runner が最後まで通る設定）

```env
MOLTBOT_GATEWAY_URL=http://<このはのIP or ドメイン>:8088
MOLTBOT_GATEWAY_SECRET=あなたのsecret
```

ローカル試行（同一マシン）: `MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088`。SECRET を空にすると Gateway は署名検証をスキップ（試行専用）。

runner 成功時は `moltbot_audit/YYYY-MM-DD/{plan_id}/` に 3層ログ＋commit_message.txt が出力される。

## API（最小）

| メソッド | パス | 概要 |
|----------|------|------|
| POST | /moltbot/plan | Plan JSON（body=planそのもの）・署名検証→保存→モック実行 |
| GET | /moltbot/plan/{plan_id}/result | 実行結果（result.json をそのまま返す） |
| POST | /moltbot/plan/{plan_id}/cancel | 状態を cancelled に |
| GET | /moltbot/health | 死活 |

## 本番運用（Phase1 やらかし防止）

- `dry_run=True` をデフォルトに（runner の Phase1 は最初 dry_run）
- `write_paths` は `~/Downloads` と移動先だけに制限
- `max_actions` は 50 程度に制限

外部公開する場合は Nginx リバプロ（/moltbot/ だけ）、ベーシック認証 or IP 制限、HTTPS（Certbot）を推奨。

## Moltbot のインストールについて

- **モックだけで試す場合**: Moltbot のインストールは**不要**。Gateway を起動するだけで、`EXECUTOR=mock`（デフォルト）で即時モック実行されます。
- **本物の Moltbot で動かす場合**: **OpenClaw（旧 Moltbot）**のインストールが**必要**です。手順は **`moltbot_gateway/deploy/INSTALL_OPENCLAW.md`**。インストール後、`MOLTBOT_DAEMON_URL` と `MOLTBOT_DAEMON_TOKEN`（または `OPENCLAW_GATEWAY_TOKEN`）を設定してください。

## B：本物 Moltbot 接続（executor 差し替え）

- `EXECUTOR=mock`（デフォルト）… モック即時実行。Moltbot 未インストールでOK。
- `EXECUTOR=moltbot` … 本物用。**Moltbot を別途インストール**したうえで、`MOLTBOT_DAEMON_URL` または `MOLTBOT_CLI_PATH` を設定。未設定なら mock にフォールバック。
- 最初は **list_files / file_read のみ許可**。他は `rejected`。解放は `executor/moltbot.py` の `ALLOWED_ACTIONS_MOLTBOT` と本物実装を足してから。

手順は `deploy/CHECKLIST_B_MOLTBOT.md` に沿って進める。

## 母艦だけでやる（このはサーバーは使わない）

- **Windows 母艦でワンクリック起動**: **`deploy\start_gateway_mothership.bat`** を実行すると 8088 で Gateway が起動する（.env に `MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088` を設定すると統合API/MCP の秘書ファイル整理が利用可能）。
- Gateway も runner も全部母艦で完結する手順は **`deploy/MOTHERSHIP_ONLY.md`** を参照。このはは使わない。

## 本格運用

**本番運用を始める**: **`deploy/PRODUCTION_START.md`** に従って上から実行。
常駐・監査ローテ・SECRET ローテ・本物接続・ロールバック・n8n: **`deploy/CHECKLIST_PRODUCTION.md`**。

**本格運用できてる？** → **`deploy/PRODUCTION_START.md`** 末尾の「本格運用できてる？ 確認コマンド」を実行。8088 の health が 200・`list_only` で監査が増えれば読み取り運用は可能。OpenClaw の exec が 404 でも `list_files` / `file_read` はローカルフォールバックで動作する。
