# MRL Memory Phase 2 運用 RUNBOOK

## 1. 障害時手順

### 1.1 API が応答しない（/health が 200 を返さない）

1. **プロセス確認**
   - タスクマネージャーで `python.exe`（mrl_memory_integration）が動いているか確認
2. **再起動**
   - `restart_mrl_memory_simple.ps1` を実行（管理者不要）
   - または手動で該当 Python プロセスを終了し、API を起動し直す
3. **ログ確認**
   - コンソール出力や `mrl_memory.log` でエラー有無を確認

### 1.2 Stop Checker が「本当のSTOP」で exit 1 になった

1. **スナップショット確認**
   - 直近の `snapshots/YYYY-MM-DD/HH.json` を開き、`metrics` の値（writes_per_min, e2e_p95_sec, contradiction_rate 等）を確認
2. **Phase 1 に戻す**
   - `.env` で `FWPKM_WRITE_ENABLED=0` に変更
   - MRL Memory API を再起動（`restart_mrl_memory_simple.ps1`）
3. **原因調査**
   - 閾値ファイル `phase2_thresholds.json` と実測値を比較
   - 必要なら閾値を緩和するか、負荷元（ManaOS 等）を確認

### 1.3 スナップショットが溜まらない（監視タスクが失敗している）

1. **タスク履歴確認**
   - タスクスケジューラで `MRL_Memory_Phase2_Auto_Monitor` の「最終実行結果」を確認
2. **手動実行**
   - `python monitor_phase2_auto.py` をプロジェクト直下で実行し、エラーメッセージを確認
3. **ログ確認**
   - `logs/phase2_auto_YYYY-MM-DD.log` に ERROR が出ていないか確認
4. **Python パス**
   - タスクの「操作」で `python.exe` が絶対パス（例: `C:\...\Python310\python.exe`）になっているか確認

---

## 2. API キー運用

### 2.1 設定場所

- `.env` に `MRL_MEMORY_API_KEY=...` または `API_KEY=...` を記載
- 本番では `MRL_MEMORY_API_KEY` を推奨（MRL 専用であることが分かる）

### 2.2 ローテーション手順

1. 新しいキーを生成（例: `python -c "import secrets; print(secrets.token_urlsafe(32))"`）
2. `.env` の `MRL_MEMORY_API_KEY` を新しい値に更新
3. **MRL Memory API を再起動**（必須。再起動しないと古いキーが使われ続ける）
4. 呼び出し元（ManaOS、監視スクリプト等）は同じ `.env` を読むため、通常は変更不要
5. 外部システムにキーを渡している場合は、その設定も新しいキーに更新

### 2.3 認証を一時的に無効にする

- `.env` で `REQUIRE_AUTH=0` に設定し、API を再起動
- 本番では推奨しない（必ず元に戻す）

---

## 3. 閾値の変更

- ファイル: `phase2_thresholds.json`
- 編集後、次回の `phase2_stop_checker.py` 実行から反映される（再起動不要）
- タスクスケジューラの引数変更は不要

---

## 4. 古いスナップショットの整理

- **確認のみ**: `python cleanup_old_snapshots.py snapshots --older-than 30 --dry-run`
- **削除実行**: `python cleanup_old_snapshots.py snapshots --older-than 30 --execute`
- 誤削除防止のため、まずは `--dry-run` で対象一覧を確認すること

---

## 5. アラート（Slack 等）

- `.env` に `PHASE2_ALERT_WEBHOOK_URL` または `SLACK_WEBHOOK_URL` を設定すると、
  Stop Checker が「本当のSTOP」で exit 1 になるタイミングで Webhook に POST する。
- 未設定の場合は何も送信しない（エラーにもならない）。

## 6. ダッシュボード・ベースライン更新

- **ダッシュボード生成**: `python generate_snapshot_dashboard.py` → `snapshot_dashboard.html` を開く。
- **ベースライン更新（週次など）**: `python update_baseline_from_snapshots.py` で直近スナップショットから中央値を計算し、`phase1_metrics_snapshot_baseline.json` を更新する。

### 6.1 定期タスク（忘れないように全部登録する場合）

**管理者 PowerShell** で以下を実行すると、4つのタスクが登録される。

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\mana4\Desktop\manaos_integrations\scripts\setup_mrl_memory_optional_tasks.ps1"
```

| タスク名 | スケジュール | 内容 |
|----------|--------------|------|
| MRL_Memory_24h_Summary_Daily | 日次 01:00 | 24hサマリーを `snapshots/` に保存 |
| MRL_Memory_Dashboard_Daily | 日次 01:15 | `snapshot_dashboard.html` を更新 |
| MRL_Memory_Baseline_Weekly | 週次 日曜 02:00 | ベースラインをスナップショットから更新 |
| MRL_Memory_Cleanup_Monthly | 月次 1日 03:00 | 30日より古いスナップショットを削除 |

確認: `Get-ScheduledTask -TaskName 'MRL_Memory_*'`

## 7. 関連ファイル一覧

| ファイル | 役割 |
|----------|------|
| `phase2_thresholds.json` | 停止判定・Go判定の閾値 |
| `phase1_metrics_snapshot_baseline.json` | Phase 1 ベースライン（差分・判定の基準） |
| `snapshots/YYYY-MM-DD/HH.json` | 時間別メトリクススナップショット |
| `logs/phase2_auto_YYYY-MM-DD.log` | 監視スクリプトのログ |
| `snapshot_dashboard.html` | ダッシュボード（generate_snapshot_dashboard.py で生成） |
| `.env` | API キー・REQUIRE_AUTH・FWPKM_* ・PHASE2_ALERT_WEBHOOK_URL 等 |

---

**更新日**: 2026-01-30
