# Runbook テンプレート仕様（復旧・整理・監視）

L4 で自動実行してよい「定義済み低リスク Runbook」の形式と、用意しているテンプレートの説明。

---

## 1. Runbook の構造（JSON）

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | string | 一意 ID。`runbooks_enabled` に列挙する値 |
| name | string | 表示名 |
| description | string | 説明 |
| action_class | string | C0 / C1 / C2 のいずれか（C3/C4 は Runbook に含めない） |
| steps | array | 実行順のステップ列 |
| conditions | object | 実行条件（スケジュール・日次上限・quiet_hours） |
| safety | object | 安全制約（許可ツール・破壊禁止・フラグ） |

### steps の 1 要素

| フィールド | 型 | 説明 |
|------------|-----|------|
| order | int | 実行順 |
| action | string | `tool` / `orchestrator` / `condition` |
| tool_name | string | action=tool のとき |
| params | object | ツール or オーケストレーターへの引数 |
| text | string | action=orchestrator のときの自然文 |
| mode | string | orchestrator の mode（例: auto） |
| condition_type | string | action=condition のとき（例: any_device_unhealthy） |
| on_failure | string | `log_and_continue` / `log_and_stop` |

### conditions

| フィールド | 説明 |
|------------|------|
| schedule | cron 式（例: `*/15 * * * *`） |
| max_daily_runs | 1日あたり最大実行回数 |
| quiet_hours_skip | true なら quiet_hours 中はスキップ |

### safety

| フィールド | 説明 |
|------------|------|
| no_destructive | 破壊的操作を行わない |
| read_only | 読み取りのみ |
| allowed_tools | 許可するツール名のリスト（未指定なら steps 内のみ） |
| recovery_requires_runbook_flag | 復旧実行に別フラグを要求する場合のキー名 |

---

## 2. 用意しているテンプレート

| ID | 名前 | 概要 |
|----|------|------|
| **health_recover** | ヘルス監視と軽微な復旧 | device_get_status/health → 不健全時はオーケストレーターに復旧提案。自動復旧はフラグ許可時のみ |
| **log_rotate** | ログ肥大時のローテーション提案 | ログサイズ確認とローテーション**提案のみ**（実行しない） |
| **inbox_scan** | Inbox スキャン | file_secretary_inbox_status → moltbot list_only。整理は提案のみ |
| **pixel7_bridge_recover** | Pixel7 ブリッジ復旧提案 | Pixel7 応答確認 → 落ちてたら再起動手順を提案。実際の再起動は L3 承認または手動 |

ファイル配置: `config/runbooks/*.json`。一覧は `config/runbooks/README.md` を参照。

---

## 3. 実行エンジン（実装済み）

- **runbook_engine.py**: L4 以上かつ `runbooks_enabled` に含まれる Runbook を、`conditions.schedule`（簡易 cron）・`max_daily_runs`・`quiet_hours_skip` に従って「due」判定し実行。
- **トリガー**: Autonomy System の `POST /api/execute` が呼ばれたときに、先に due な Runbook を実行してから通常タスクを実行。外部スケジューラが定期的に `/api/execute` を叩く運用を想定。
- **ステップ実行**: `action=tool` / `action=orchestrator` は Orchestrator の `POST /api/execute` に自然文で依頼。`action=condition` は前ステップの結果（`any_device_unhealthy` / `bridge_down`）で分岐。
- **runbook_flags**: 設定の `runbook_flags.health_recover_allow_restart` 等が true のとき、オーケストレーターへのテキストに「自動復旧は許可されています」を付与。false なら「提案のみ」を付与。
- **状態**: `autonomy_runbook_state.json`（`budget_usage_dir` と同じディレクトリ）に Runbook ごとの `last_run`・`runs_today`・`day_start` を保存。
- 実行開始・各ステップ・終了は **監査ログ（Gate D）** に plan_id = Runbook id、action_id = step order 等で記録。
- Runbook 内では C2 まで（ツール呼び出しは Orchestrator 経由のため実質 C0〜C2）。C3/C4 は Runbook に含めない。

---

## 4. 運用メモ

- 新規 Runbook を足すときは `action_class` を C2 までにし、`safety` を明示する。
- `health_recover_allow_restart` や `pixel7_bridge_allow_restart` などのフラグは、設定または環境変数で「許可時のみ復旧手順を実行に含める」ようにする想定。
- まずは **inbox_scan** と **log_rotate**（読み取り＋提案のみ）で L4 動作を確認し、その後 **health_recover** / **pixel7_bridge_recover** を有効化するのが安全。
