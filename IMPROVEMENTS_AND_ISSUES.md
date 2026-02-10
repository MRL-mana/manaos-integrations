# 改善・強化の実施内容と問題点

## 実施した改善・強化

### 2026-02-06 実施分（構成・ドキュメント整理）

| # | 項目 | 内容 |
|---|------|------|
| A | ハードコードパスの動的取得 | `add_all_mcp_servers_to_cursor.ps1`, `manaos_unified_mcp_server/add_to_cursor_mcp.ps1` で `$PSScriptRoot` からプロジェクトパスを自動取得 |
| B | MCP サーバー役割の明記 | `docs/guides/MCP_SERVERS_GUIDE.md` に unified-api と manaos-* の使い分け、専用 MCP の役割を追記 |
| C | konoha_mcp_servers アーカイブ扱い | `konoha_mcp_servers/README.md` を新規作成し、メイン MCP はリポジトリ直下であることを明記 |
| D | Skills と MCP の使い分け一元化 | `docs/guides/SKILLS_AND_MCP_GUIDE.md` を新規作成、判断フロー・関連ドキュメントを整理 |
| E | check_manaos_stack 拡張 | `-Extended` で 5108/5112/5120/5121/5559/5111 の疎通も確認可能に |
| F | 起動依存関係のドキュメント化 | `docs/guides/STARTUP_DEPENDENCY.md` を新規作成 |
| G | env.example のセクション分け | 必須 / 推奨 / オプションで整理、参照しやすく再構成 |
| H | config/ README | `config/README.md` で設定ファイルの役割を説明 |

---

### 過去実施分

| # | 項目 | 内容 |
|---|------|------|
| 1 | 閾値の外部化 | `phase2_thresholds.json` で閾値を変更可能。`phase2_stop_checker.py` が起動時に読み込む。 |
| 2 | 本当のSTOPだけ exit 1 | `--scheduler` 時、「判定不能」は exit 0、「本当のSTOP」は exit 1。タスク履歴で本当に止めるべきときだけ赤になる。 |
| 3 | cwd / .env の安定化 | `phase1_metrics_snapshot.py` 起動時にスクリプト基準で cwd と .env を設定。タスクスケジューラからでも安定動作。 |
| 4 | 監視ログのファイル出力 | `monitor_phase2_auto.py` が `logs/phase2_auto_YYYY-MM-DD.log` に成功/失敗を追記。 |
| 5 | 古いスナップショット整理 | `cleanup_old_snapshots.py snapshots --older-than 30 --dry-run` / `--execute`。誤削除防止でまず --dry-run 推奨。 |
| 6 | RUNBOOK | `MRL_MEMORY_RUNBOOK.md` に障害時手順・APIキー運用・閾値・アラート・ダッシュボードを記載。 |
| 7 | 簡易ダッシュボード | `generate_snapshot_dashboard.py` で `snapshot_dashboard.html` を生成。ブラウザで開いてスナップショット一覧を確認。 |
| 8 | STOP アラート | `.env` の `PHASE2_ALERT_WEBHOOK_URL` または `SLACK_WEBHOOK_URL` を設定すると、本当のSTOP 時に Webhook に POST。未設定なら何もしない。 |
| 9 | ベースライン更新 | `update_baseline_from_snapshots.py` で直近スナップショットから中央値を計算し、`phase1_metrics_snapshot_baseline.json` を更新。週次運用向け。 |

---

## 問題点・注意点（全部やった場合）

### 1. タスクスケジューラの引数変更は不要
- 閾値は `phase2_thresholds.json` を編集するだけ。Stop Checker のタスク引数はそのままでよい。
- 既存の「--scheduler」付きタスクは、**本当のSTOP のときだけ** exit 1 になる。判定不能のときは今まで通り exit 0。

### 2. 本当のSTOP でタスクが「失敗」になる
- スケジューラで「本当のSTOP」になると、タスクの「最終実行結果」が 1（失敗）になる。
- **意図どおり**（止めるべきときは赤になる）。アラート Webhook を設定していれば Slack 等にも届く。

### 3. アラート Webhook は未設定でよい
- `PHASE2_ALERT_WEBHOOK_URL` / `SLACK_WEBHOOK_URL` が無い場合は POST をスキップするだけ。エラーにはならない。

### 4. 古いスナップショット削除は手動 or 別タスクで
- `cleanup_old_snapshots.py --execute` は**削除を実行する**。定期実行する場合は「30日以上」等のルールを決め、まず --dry-run で確認すること。
- タスクスケジューラに登録する場合は「月1回 --execute」など、運用方針を RUNBOOK に書いておくとよい。

### 5. ベースライン更新のタイミング
- `update_baseline_from_snapshots.py` は**既存の baseline を上書き**する。週次などで「直近の傾向を反映したい」ときに実行。
- 実行頻度を上げすぎると、一時的なノイズで閾値判定が緩くなる可能性がある。週1回程度を目安に。

### 6. phase1_metrics_snapshot の cwd 変更
- 起動時に `os.chdir(スクリプトの親)` する。**他ツールが同じプロセスから snapshot を呼ばない限り**影響はない。ManaOS 等は別プロセスなので問題なし。

---

## 運用の確認

- **監視ログ**: 次回の Auto Monitor 実行後、`logs/phase2_auto_YYYY-MM-DD.log` に 1 行追記される。
- **ダッシュボード**: `python generate_snapshot_dashboard.py` 実行後、`snapshot_dashboard.html` をブラウザで開く。
- **閾値**: `phase2_thresholds.json` を編集してから `phase2_stop_checker.py` を実行すれば反映される（再起動不要）。

---

**更新日**: 2026-02-06（2026-02-06 実施分を追記）
