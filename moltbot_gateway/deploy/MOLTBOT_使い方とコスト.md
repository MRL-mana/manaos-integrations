# Moltbot × まなOS の使い方とお金の話

## 自動で起動・自動で使用できる？

**はい。両方できます。**

### 自動で起動（ログオン時・落ちたら復旧）

| やること | スクリプト | 説明 |
|----------|------------|------|
| Moltbot Gateway (8088) をログオン時に起動 | `register_gateway_autostart.ps1` | 1回実行でタスク登録。以降ログオンで起動。 |
| OpenClaw Gateway (18789) をログオン時に起動 | `register_openclaw_gateway_autostart.ps1` | OpenClaw をサービスなしで常駐させるときに使用。 |
| 5分おきに 8088/18789 を監視して落ちてたら再起動 | `register_heal_manaos_services_every5min.ps1` | 自動復旧用。1回実行でタスク登録。 |

**手順（リポジトリルートで）:**

```powershell
# Gateway をログオン時に起動
.\moltbot_gateway\deploy\register_gateway_autostart.ps1

# （本物 OpenClaw を使う場合）OpenClaw もログオン時に起動
.\moltbot_gateway\deploy\register_openclaw_gateway_autostart.ps1

# 5分おきに自動復旧を登録（推奨）
.\moltbot_gateway\deploy\register_heal_manaos_services_every5min.ps1
```

### 自動で使用（定期実行）

| やること | スクリプト | 説明 |
|----------|------------|------|
| 毎日決まった時刻に list_only を実行 | `register_moltbot_daily_list_only.ps1` | デフォルト 08:00。時刻は `$env:MOLTBOT_DAILY_TIME="09:00"` で変更可能。 |

**手順:**

```powershell
# 毎日 08:00 に list_only を実行するタスクを登録
.\moltbot_gateway\deploy\register_moltbot_daily_list_only.ps1

# 09:00 にしたい場合（登録前に環境変数）
$env:MOLTBOT_DAILY_TIME = "09:00"
.\moltbot_gateway\deploy\register_moltbot_daily_list_only.ps1
```

- 定期実行時も **Moltbot Gateway (8088)** が動いている必要がある。上記「自動で起動」を登録しておくこと。
- 結果は従来どおり `moltbot_audit\YYYY-MM-DD\plan-xxx\` に残る。

**一括登録（自動起動＋自動復旧＋毎日 list_only をまとめて登録）:**

```powershell
.\moltbot_gateway\deploy\register_moltbot_auto_all.ps1
```

上記 4 つ（Gateway 起動 / OpenClaw 起動 / 5分おき復旧 / 毎日 list_only）をまとめてタスク登録する。

---

## どう使えばいい？

### パターン1: コマンド（CLI）で使う

1. **Gateway を起動**（1回だけ、またはログオン時に自動起動）

   ```powershell
   .\moltbot_gateway\deploy\run_gateway_wrapper_production.ps1
   ```
   常駐させたい場合: `.\moltbot_gateway\deploy\register_gateway_autostart.ps1` を実行してタスク登録。

2. **.env を設定**（リポジトリルートの `.env`）

   ```env
   MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088
   MOLTBOT_GATEWAY_SECRET=好きな秘密文字列
   ```

3. **実行**

   ```powershell
   # フォルダ一覧だけ取得（list_files）
   python manaos_moltbot_runner.py list_only

   # 特定フォルダを指定
   python manaos_moltbot_runner.py list_only --path "C:\Users\mana4\Documents"

   # ファイルの中身を読む（file_read）
   python manaos_moltbot_runner.py read_only --path "C:\Users\mana4\Downloads\メモ.txt"
   ```

   結果は `moltbot_audit\YYYY-MM-DD\plan-xxx\` に残る。

---

### パターン2: 統一API（HTTP）で使う

n8n・Open WebUI・自分で書いたスクリプトから HTTP で呼べる。

1. **Moltbot Gateway (8088)** と **統一API (9500)** を起動する。
2. `.env` に `MOLTBOT_GATEWAY_URL` と `MOLTBOT_GATEWAY_SECRET` を書く（統一APIがこの値で Gateway に接続する）。
3. 例:

   ```powershell
   # Plan 送信（list_only）
   Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:9500/api/moltbot/plan" `
     -ContentType "application/json" -Body '{"intent":"list_only","path":"~/Downloads"}'

   # 結果取得（返ってきた plan_id を指定）
   Invoke-RestMethod -Uri "http://127.0.0.1:9500/api/moltbot/plan/plan-YYYYMMDD-HHMMSS/result"

   # 秘書経由（学習・記憶と連携）
   Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:9500/api/secretary/file-organize" `
     -ContentType "application/json" -Body '{"path":"~/Downloads","user_hint":"一覧取得"}'
   ```

   疎通確認だけなら: `.\moltbot_gateway\deploy\check_unified_api_moltbot.ps1`

---

### パターン3: コードから使う（自律・秘書）

Python で「ファイル整理 Plan を投げる」だけなら:

```python
from personality_autonomy_secretary_integration import PersonalityAutonomySecretaryIntegration
i = PersonalityAutonomySecretaryIntegration()
r = i.submit_file_organize_plan(user_hint="Downloads確認", path="~/Downloads", intent="list_only")
# r["ok"] == True なら r["plan_id"], r["data"]
```

---

## お金かかるの？

**この Moltbot 連携そのものはお金かかりません。**

| もの | どこで動く | お金 |
|------|------------|------|
| Moltbot Gateway | あなたの PC（8088） | かからない（自前サーバー） |
| OpenClaw | あなたの PC（18789） | かからない（オープンソース・ローカル） |
| 統一API | あなたの PC（9500） | かからない（自前サーバー） |
| list_only / read_only | 上記の上で動く | かからない |

- **クラウドの Moltbot サービスにはつながっていない**ので、利用料・従量課金は発生しません。
- **OpenClaw** は npm で入れるオープンソースで、ローカルで動かすだけなら追加費用なしです。
- **n8n を n8n.cloud で使っている**など、別のサービスに課金している場合はその分だけかかります。Moltbot 連携の「API を叩く」こと自体に課金はありません。

まとめ: **全部自分の環境で動かす前提なら、Moltbot の使い方による追加のお金はかかりません。**

---

## Cursor / VS Code から使う

**タスクとして登録済み**なので、エディタ内だけで完結する。

1. **コマンドパレット**を開く
   - VS Code / Cursor: `Ctrl+Shift+P`（Mac: `Cmd+Shift+P`）
2. **「Tasks: Run Task」** を選ぶ
3. 一覧から次のいずれかを選んで実行

| タスク名 | 内容 |
|----------|------|
| **Moltbot: Gateway 起動** | Moltbot Gateway (8088) を起動（バックグラウンド） |
| **Moltbot: list_only（フォルダ一覧）** | `~/Downloads` の一覧を取得 |
| **Moltbot: list_only（パス指定）** | 実行時にパスを入力して一覧取得 |
| **Moltbot: read_only（ファイル読取）** | 実行時にファイルパスを入力して内容を取得 |
| **Moltbot: 統一API疎通確認** | 統一API (9500) 経由で Moltbot を呼ぶ一連の疎通確認 |

- **パス指定**・**read_only** を選ぶと、入力欄が表示される。例: `~/Downloads` や `C:\Users\mana4\Documents`。
- **list_only / read_only** は、先に **Moltbot: Gateway 起動** を実行しておく（または別ターミナルで Gateway を起動しておく）。
- **統一API疎通確認** は、統一API (9500) と Gateway (8088) の両方が起動している状態で実行する。

**Cursor のチャットから**
「list_only して」「Downloads の一覧取って」などと書くと、AI がタスク実行や `python manaos_moltbot_runner.py list_only` を提案してくれる。そのまま実行すればよい。
