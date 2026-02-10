# 自律レベル設計（L0〜L6 + ゲート）

自律レベルは「強さ」ではなく**権限セット（Scope + Guards）**として扱う。

- **Scope**: 通知だけ / 調査まで / 実行まで / 破壊的操作まで
- **Guards**: Action Class・Confirm Token・予算・監査・quiet_hours

## レベル定義（L0〜L6）

| レベル | 名前 | できること |
|--------|------|------------|
| L0 | OFF | 自律実行なし。手動のみ |
| L1 | Observe | health/status 収集、ログ集計、提案生成（実行しない） |
| L2 | Notify | L1 + 秘書ルーチン（通知）、Obsidian/Rows 追記のみ |
| L3 | Assist | L2 + 計画・評価・**承認後に** n8n/Drive/MoltBot 実行 |
| L4 | Act | L3 + 定義済み低リスク Runbook の自動実行 |
| L5 | Autopilot | L4 + ルーティング最適化・失敗学習。設定変更は二重ゲート |
| L6 | Ops | L5 + Docker・緊急WF・強制再起動。**インシデント時のみ一時的に** |

## ゲート 4 点セット

1. **Gate A: Action Class**
   全アクションを C0〜C4 に分類。レベルごとに許可クラスを固定。
   実装: `autonomy_gates.py` の `TOOL_ACTION_CLASS` と `LEVEL_ALLOWED_ACTION_CLASSES`。

2. **Gate B: Confirm Token**
   C3/C4 は重要操作のため Confirm Token 必須（L4 でも C3/C4 は承認待ち）。
   - **allowlist**: `confirm_tokens_allowlist` に固定トークンを列挙。
   - **一時トークン**: `POST /api/approvals` で1回限りトークン発行（消費で無効化）。
   - **時間ベース HMAC**: `confirm_token_hmac_secret` と `confirm_token_hmac_window_seconds` を設定すると、`autonomy_gates.generate_hmac_confirm_token` / `verify_hmac_confirm_token` で検証（前後1窓で時計ずれ許容）。

3. **Gate C: 予算**
   1時間/1日あたりの llm_calls / image_jobs / video_jobs に上限。
   枠超過時は **degrade_policy.on_budget_exceeded** で降格（推奨 L2）。

4. **Gate D: 監査**
   全自律アクションに plan_id / action_id / input_hash / result を付与し JSONL に記録。

## 設定ファイル

- **config/autonomy_level_config.json**
  レベル・予算・quiet_hours・degrade_policy・runbooks_enabled 等。
  例: `config/autonomy_level_config.example.json` をコピーして使用。

- **autonomy_config.json**（従来）
  引き続き `autonomy_level`（整数 0〜6 または旧文字列）や `tasks_storage_path` を読み込む。
  `config/autonomy_level_config.json` が存在すればマージされる。

## 運用のおすすめ（マナ向け）

- **平常**: L4（Runbook 自動）
- **大物生成（動画・大量）**: L3（承認制）
- **Docker/緊急**: L6（Confirm Token 必須＋時間制限、例: 15分だけ）

## API（自律レベル・承認・ダッシュボード）

- **GET /api/level** … 現在の自律レベル（0〜6）と名前を返す。
- **POST /api/level** … レベルを変更。body: `{"level": 4}` または `{"autonomy_level": 4}`。L5/L6 への変更は `confirm_token` 付与を推奨。
- **POST /api/check-tool** … ツール実行可否（Gate A+B）。body: `{"tool_name": "...", "confirm_token": "..."?}`。
- **POST /api/record-cost** … 予算記録。body: `{"usage_key": "llm_calls|image_jobs|video_jobs", "period": "per_hour|per_day", "amount": 1}`。
- **POST /api/approvals** … 1回限り有効な Confirm Token を発行（「この1回だけ許可」）。body: `{"tool_name": "llm_chat"?,"expires_in_seconds": 300?}`。返却の `confirm_token` を check-tool や MCP 呼び出し時に渡す。
- **GET /api/dashboard** … Portal/ダッシュボード用。レベル・予算使用量・Runbook 最終実行・監査ログ末尾をまとめて返す。

## 関連ファイル・ドキュメント

| 種類 | パス |
|------|------|
| ゲート実装 | `autonomy_gates.py` |
| 自律システム | `autonomy_system.py` |
| Runbook 実行エンジン | `runbook_engine.py` |
| レベル設定スキーマ | `config/autonomy_level_schema.json` |
| レベル設定例 | `config/autonomy_level_config.example.json` |
| **Action Class 一覧** | [docs/AUTONOMY_ACTION_CLASS_LIST.md](./AUTONOMY_ACTION_CLASS_LIST.md) |
| **レベル別許可マトリクス** | [docs/AUTONOMY_LEVEL_MATRIX.md](./AUTONOMY_LEVEL_MATRIX.md) |
| **降格ルール・失敗カウンタ** | [docs/AUTONOMY_DEGRADE_SPEC.md](./AUTONOMY_DEGRADE_SPEC.md) |
| **Runbook テンプレ仕様** | [docs/AUTONOMY_RUNBOOK_SPEC.md](./AUTONOMY_RUNBOOK_SPEC.md) |
| Runbook テンプレ配置 | `config/runbooks/*.json` |
| **Portal 自律UI** | Portal 起動後 `GET http://localhost:5108/autonomy-dashboard` でレベル・予算・承認ボタン・**レベル変更**を表示。 |
| **クイックスタート** | `scripts/start_autonomy_portal_dashboard.ps1` で Autonomy + Portal を起動し、ダッシュボードをブラウザで開く。 |
| **HMAC トークン生成** | `AUTONOMY_HMAC_SECRET` を設定して `python scripts/autonomy_hmac_token.py` で現在窓のトークンを表示。 |
| Runbook スケジュール | `croniter` 利用時は cron 厳密解釈。未導入時は簡易判定にフォールバック。 |
