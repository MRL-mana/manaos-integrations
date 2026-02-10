# 自己観察（Phase1 / Phase2）クイックスタート

**目的**: `/api/llm/chat` で振り返りログを記録し、同一テーマ再訪時に過去の振り返りメモを注入するまでを最短で動かす。

---

## ManaOS 統合状況

| 対象 | 統合内容 |
|------|----------|
| **Unified API Server** (`unified_api_server.py`) | `/api/llm/chat` が Phase1/Phase2 の**唯一の入口**。`PHASE1_REFLECTION` が on/off のとき thread_id/turn_id を管理し、会話・振り返りをログに記録。`PHASE2_MEMO_INJECT=on` のとき同一テーマの過去メモを最後のユーザー発話の先頭に注入。`PHASE2_MEMO_APPEND=on` のとき振り返りを phase2 メモにリアルタイム追記（phase1_hooks 内）。 |
| **ManaOS 統合 MCP** (`manaos_unified_mcp_server`) | Phase1/Phase2 の**全ツール**を MCP で提供（一括実行・週次レポート・集計・バックフィル・メモ取得・自動整理など）。Cursor の MCP「manaos-unified」から呼び出し可能。 |
| **レスポンス** | `/api/llm/chat` の JSON に `thread_id` / `turn_id` / `request_id` を返す（Phase1 実験時）。クライアントは同一スレッドで `thread_id` を送ると継続率・テーマ再訪の計測が正しく動く。 |

環境変数で有効化するだけで、**ManaOS のチャット経路と完全に統合**されている。

---

## 1. 環境変数（.env または起動前）

| 変数 | 意味 | 推奨 |
|------|------|------|
| `PHASE1_REFLECTION` | `on` = 振り返りLLM呼び出し＋ログ / `off` = ログのみ | 実験時は `on` |
| `PHASE2_MEMO_APPEND` | `on` = 振り返りを記録するたびに phase2 メモに追記 | メモ蓄積したいとき `on` |
| `PHASE2_MEMO_INJECT` | `on` = 同一テーマの過去メモを応答前に注入 | 再訪時に参照したいとき `on` |

例（メモ蓄積＋注入まで有効）:

```bash
PHASE1_REFLECTION=on
PHASE2_MEMO_APPEND=on
PHASE2_MEMO_INJECT=on
```

---

## 2. API 起動

```powershell
cd c:\Users\mana4\Desktop\manaos_integrations
$env:PHASE1_REFLECTION="on"; $env:PHASE2_MEMO_APPEND="on"; $env:PHASE2_MEMO_INJECT="on"
python -m unified_api_server
```

`/api/llm/chat` に POST で会話すると:

- Phase1: 会話ログ・振り返りログが `phase1_conversation.log` / `phase1_reflection.log` に追記される。
- Phase2: 振り返りが出るたびに `phase2_reflection_memos.jsonl` に追記され、同一テーマ再訪時にそのメモが最後のユーザー発話の先頭に付与される。

---

## 3. 集計・レポート（手動 or MCP）

### 一気に全部やる

1コマンド／1回の MCP 呼び出しで「集計 → 低満足度 → バックフィル → メモ概要 → アーカイブ → 履歴表示」まで実行する。

| 方法 | コマンド / MCP |
|------|-----------------|
| 一括実行（保存なし） | `python phase1_phase2_full_run.py` / MCP `phase1_phase2_full_run` |
| 一括実行（先にスナップショット保存） | `python phase1_phase2_full_run.py --save` / MCP `phase1_phase2_full_run`（`save: true`） |

オプション: `--history-tail N`（履歴表示の直近件数）、`--tag`（保存時のタグ）。MCP では `history_tail`, `tag`, `condition` を指定可能。

---

| やりたいこと | コマンド / MCP ツール |
|--------------|------------------------|
| 継続率・テーマ再訪・満足度・テーマ出現回数分布 | `python phase1_aggregate.py` / `phase1_aggregate` |
| 週次レポート（集計＋低満足度） | `python phase1_weekly_report.py` / `phase1_weekly_report`（`--phase2` で Phase2 メモ概要を末尾に追加） |
| 満足度1〜2の理由集約 | `python phase1_low_satisfaction.py` / `phase1_low_satisfaction` |
| 既存 phase1 ログからメモ投入 | `python phase2_backfill_memos.py` / `phase2_backfill_memos` |
| テーマIDでメモ取得 | MCP `phase2_get_memos`（`theme_id` を指定） |
| Phase2 メモのテーマ別件数・満足度平均 | `python phase2_memo_summary.py` / `phase2_memo_summary` |
| 低満足度の履歴を1行追記 | `python phase1_low_sat_archive.py` / `phase1_low_sat_archive` |
| 低満足度履歴の表示（直近N件） | `python phase1_low_sat_history_view.py -n 10` / `phase1_low_sat_history_view`（`tail` 指定可） |
| 週次レポートをタスク登録 | `.\schedule_phase1_weekly_report.ps1`（レポート＋アーカイブを実行。解除: `-Unregister`、保存付き: `-WithSave`） |
| Phase2 メモの .bak を圧縮退避 | `python phase2_archive_memo_backup.py --delete-bak`（ZIP保存→.bak削除） |
| Phase2 自動整理（dedup→ZIP退避） | `python phase2_auto_cleanup.py` / MCP `phase2_auto_cleanup` |

---

## 4. よくある流れ

1. **初回**: `PHASE1_REFLECTION=on` で会話 → 振り返りログが溜まる。
2. **メモを溜める**: `PHASE2_MEMO_APPEND=on` にすると、振り返りが出るたびに phase2 メモに追記される（バックフィル不要）。
3. **同一テーマで再訪**: `PHASE2_MEMO_INJECT=on` にすると、過去の振り返りメモが応答前に注入される。
4. **週次確認**: `phase1_weekly_report`（必要なら `--save`、`--phase2` で Phase2 メモ概要も）で継続率・低満足度・メモ概要を確認。
5. **メモの中身確認**: `phase2_memo_summary` でテーマ別件数・満足度を一覧。
6. **週次レポートを自動実行**: `.\schedule_phase1_weekly_report.ps1` で日曜 9:00 に「レポート＋低満足度アーカイブ」を登録。解除は `-Unregister`。保存付きなら `-WithSave`。
7. **低満足度の履歴を溜める**: `python phase1_low_sat_archive.py` で満足度1〜2の件数と理由トップ5を `phase1_low_sat_history.jsonl` に1行追記。週次レポートのあとに実行すると時系列で傾向を追える。

詳細は `docs/PHASE1_SELF_OBSERVATION_EXPERIMENT.md` と `docs/PHASE2_SELF_OBSERVATION_DESIGN.md` を参照。
