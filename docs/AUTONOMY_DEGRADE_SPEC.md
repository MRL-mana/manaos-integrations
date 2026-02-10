# 降格ルール（degrade_policy）と失敗カウンタ仕様

自律レベルを「事故防止」のため自動で下げる条件と、失敗カウンタの扱いを定義する。

---

## 1. 降格トリガーと降格先

| トリガー | 設定キー | デフォルト降格先 | 説明 |
|----------|----------|------------------|------|
| **予算超過** | `degrade_policy.on_budget_exceeded` | **L2** | 1時間/1日の llm_calls / image_jobs / video_jobs のいずれかが上限を超えたとき |
| **連続失敗** | `degrade_policy.on_repeated_failures` | **L3** | 自律タスクの連続失敗回数が閾値に達したとき |

- 降格先は 0〜6 の整数で指定。常用は「予算超過→L2」「連続失敗→L3」を推奨。
- 降格は **Autonomy System の稼働中**にのみ適用。再起動時は設定ファイルの `autonomy_level` がそのまま使われる。

---

## 2. 予算超過（Gate C）

### 2.1 流れ

1. 自律またはオーケストレーター経由で **C3 に該当するアクション**（LLM 呼び出し・画像生成・動画生成）を実行する**前**に、`check_budget(config, usage_key, period)` で枠内か確認。
2. 実行**後**に `record_cost(usage_key, period, amount)`（または `increment_budget_usage`）で使用量を加算。
3. 加算後の値が **per_hour / per_day の上限以上**になった時点で「予算超過」とみなし、`get_degraded_level(config, "on_budget_exceeded")` で得たレベルに **set_level_int** する。
4. これにより、以降は L2 であれば C3/C4 は許可されず、コストの暴走を防ぐ。

### 2.2 usage_key と period

- **usage_key**: `llm_calls` | `image_jobs` | `video_jobs`
- **period**: `per_hour` | `per_day`
- 使用量は `autonomy_budget_usage.json` に保存。1時間経過・日付変更で該当カウンタはリセットされる（`_reset_if_new_period`）。

### 2.3 設定例

```json
"budget": {
  "per_hour": { "llm_calls": 50, "image_jobs": 10, "video_jobs": 2 },
  "per_day":  { "llm_calls": 500, "image_jobs": 80, "video_jobs": 10 }
},
"degrade_policy": {
  "on_budget_exceeded": 2
}
```

- 上限を設けない場合は `-1`。

---

## 3. 連続失敗カウンタ

### 3.1 対象

- **Autonomy System** の `check_and_execute_tasks()` で実行した**自律タスク**のみが対象。
- 各タスク実行結果が `status: "failed"` または `status: "error"` のとき「失敗」とカウント。

### 3.2 流れ

1. タスク実行後、結果が failed/error なら **consecutive_failures** を +1。
2. 成功なら **consecutive_failures** を 0 にリセット。
3. `consecutive_failures >= on_repeated_failures_threshold` になったら、`get_degraded_level(config, "on_repeated_failures")` で得たレベルに **set_level_int** し、ログに「連続失敗のためレベル降格」を出力。
4. 降格後もカウンタはリセットしない（次の成功で 0 になる）。必要なら手動でレベルを戻す。

### 3.3 設定

| キー | 型 | デフォルト | 説明 |
|------|-----|------------|------|
| `degrade_policy.on_repeated_failures` | int (0〜6) | 3 | 連続失敗時の降格先レベル |
| `degrade_policy.on_repeated_failures_threshold` | int (≥1) | 5 | 何回連続失敗で降格するか |

### 3.4 実装上の保持場所

- `AutonomySystem._consecutive_failures`（メモリ上のみ。再起動で 0 に戻る）。

---

## 4. レベル復帰

- **自動復帰は行わない**。意図的にレベルを上げる場合は次のいずれか:
  - 設定ファイルの `autonomy_level` を変更し、Autonomy System を再起動する。
  - （将来）API で `set_level_int(level)` を呼ぶ管理用エンドポイントを用意する。
- L6 は「15分だけ」など**時間制限**を運用で決め、期限後に手動で L4 等に下げることを推奨。

---

## 5. 監査との関係

- 降格が発生した場合も、**監査ログ（Gate D）** には通常どおり「タスク実行」の 1 行が記録される。
- 降格そのものを専用エントリで残す場合は、`audit_log(..., result="degraded", message=理由)` のような拡張を検討可能。

---

## 6. まとめ

| 項目 | 内容 |
|------|------|
| 予算超過 | 枠超えで即時 `on_budget_exceeded` レベルへ降格（推奨 L2） |
| 連続失敗 | 閾値回数で `on_repeated_failures` レベルへ降格（推奨 L3） |
| カウンタ | 失敗で +1、成功で 0。再起動で 0。 |
| 復帰 | 自動復帰なし。設定変更または手動 API で復帰。 |

実装: `autonomy_system.py`（`record_cost`、`check_and_execute_tasks` 内の失敗時処理）、`autonomy_gates.py`（`check_budget`、`get_degraded_level`、`load_budget_usage`）。
