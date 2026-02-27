# Reason Enum Reference

このファイルは、監視/ステータス系スクリプトで出力する `latest_ok_reason` / `ok_reason` の語彙を固定するための基準です。

## `latest_ok_reason`（status系）

- `from_ok_field`  
  監視JSONの `ok` / `overall.ok` フィールドから直接判定。
- `from_issues_count`  
  `issues` の件数（0件=OK）から判定。
- `from_component_fields`  
  コンポーネント状態（例: OpenWebUI/port/tailscale, unified/comfyui）から合成判定。
- `from_failed_count`  
  失敗件数（`failed`）から判定。
- `from_r12_latest_failed`  
  `r12_latest_failed` から判定。
- `from_failure_category`  
  `failure_category` が失敗カテゴリであることから判定。
- `from_last_result`  
  Task Scheduler の `Last Result` から判定。
- `result_missing`  
  `Last Result` が取得できない。
- `result_unparseable`  
  `Last Result` はあるがパース不能。
- `task_not_found`  
  対象タスクが見つからない。
- `source_missing`  
  監視の元データ（summary/log/json出力）が見つからない。
- `ok_missing`  
  判定に必要な信号がなく、OK/NGを決定できない。

## `ok_reason`（quick系）

- `healthy`  
  問題なし。
- `from_task_state`  
  タスク状態の異常に起因。
- `from_last_result`  
  Last Result の異常に起因。
- `from_latest_failed`  
  最新失敗件数 (`failed`) に起因。
- `from_log_age`  
  ログ鮮度（stale）に起因。
- `from_log_parse`  
  ログパース失敗に起因。
- `from_log_missing`  
  ログ欠損/空に起因。
- `from_issues`  
  上記以外の issue に起因。
- `task_not_found`  
  対象タスクが見つからない。

## 運用ルール

- 新しい reason を追加する場合は、このファイルへ先に追記してから実装する。
- 既存 reason の意味を変更する場合は、互換性影響を明記する。
- 欠損系 reason は `source_missing` / `ok_missing` のいずれかを優先して使う。
