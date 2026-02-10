# Runbook テンプレート

L4 で自動実行してよい「定義済み低リスク Runbook」のテンプレート集。
`autonomy_level_config.json` の `runbooks_enabled` に ID を列挙すると、その ID の Runbook のみ L4 で実行対象になる。

- 各 JSON は **id / name / description / action_class / steps / conditions / safety** を持つ。
- **action_class** は C2 まで（C3/C4 は Runbook 内でも承認前提）。
- **steps** は実行順のアクション列。tool または orchestrator を指定。
