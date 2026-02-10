# 自律レベル別 許可マトリクス

レベルごとに許可する Action Class を一覧で示す。✓ = 許可、✗ = 不可。C3/C4 は許可されていても **Confirm Token 必須**（L6 は運用時のみ・条件付き）。

---

## レベル × Action Class

| レベル | 名前 | C0 Read-only | C1 Append | C2 Reversible | C3 Costly | C4 Destructive |
|--------|------|:------------:|:---------:|:-------------:|:---------:|:--------------:|
| **L0** | OFF | ✗ | ✗ | ✗ | ✗ | ✗ |
| **L1** | Observe | ✓ | ✗ | ✗ | ✗ | ✗ |
| **L2** | Notify | ✓ | ✓ | ✗ | ✗ | ✗ |
| **L3** | Assist | ✓ | ✓ | ✓ | ✗* | ✗* |
| **L4** | Act | ✓ | ✓ | ✓ | ✗* | ✗* |
| **L5** | Autopilot | ✓ | ✓ | ✓ | ✗* | ✗* |
| **L6** | Ops | ✓ | ✓ | ✓ | ✓** | ✓** |

\* L3〜L5 では C3/C4 は「承認後に実行」のため、自律の自動実行としては許可しない。手動または Confirm Token 付きで別経路から実行可能にする運用を想定。
\** L6 はインシデント時のみ。Confirm Token（＋時間制限・IP 制限等）必須。

---

## レベル別「できること」要約

| レベル | 自律でできること |
|--------|------------------|
| L0 | なし（手動のみ） |
| L1 | health/status 収集、ログ集計、提案生成（実行しない） |
| L2 | L1 ＋ 秘書ルーチン（通知）、Obsidian/Rows 追記のみ |
| L3 | L2 ＋ 計画・評価・**承認後に** n8n/Drive/MoltBot 等 |
| L4 | L3 ＋ **定義済み低リスク Runbook** の自動実行（C2 まで） |
| L5 | L4 ＋ ルーティング最適化・失敗学習。設定変更は二重ゲート |
| L6 | L5 ＋ Docker・緊急 WF・強制再起動（運用時のみ・ゲート厳格） |

---

## ツール種別 × レベル（抜粋）

| 種別 | L0 | L1 | L2 | L3 | L4 | L5 | L6 |
|------|----|----|----|----|----|----|-----|
| device_get_*, cache_stats, phase1_aggregate 等（C0） | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| obsidian_create_note, rows_send_data, notification_send（C1） | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| secretary_*_routine, file_secretary_organize, moltbot_submit_plan（C2） | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |
| llm_chat, comfyui_generate_image, svi_generate_video（C3） | ✗ | ✗ | ✗ | 承認後 | 承認後 | 承認後 | ✓* |
| n8n_execute_workflow, autonomy_execute_tasks, *_execute（C4） | ✗ | ✗ | ✗ | 承認後 | 承認後 | 承認後 | ✓* |

\* L6 でも Confirm Token 必須。

---

## 実装との対応

- 判定ロジック: `autonomy_gates.py` の `LEVEL_ALLOWED_ACTION_CLASSES` と `action_allowed_at_level(level, action_class)`。
- ツール→クラス: `TOOL_ACTION_CLASS`（一覧は [AUTONOMY_ACTION_CLASS_LIST.md](./AUTONOMY_ACTION_CLASS_LIST.md) を参照）。
