# System 3 改善点と強化ポイント

**更新**: 2026-01-30

**実装状況**: 2.1〜2.8 すべて実装済み（2026-01-30）

---

## 1. 改善点（現状のギャップ）

### 1.1 ToDo品質ループが提案側で未使用
- **現象**: 却下理由は `todo_quality_improvement` で記録され、`todo_quality_config.json`（禁止タグ・禁止カテゴリ・粒度・時間帯）が更新されるが、**提案生成時に参照していない**。
- **影響**: 同じパターンの却下が繰り返されやすい。改善ループが「記録→更新」で止まり、「提案フィルタ」まで繋がっていない。
- **該当**: `intrinsic_motivation.generate_intrinsic_tasks()` は `quality_config` を一切読んでいない。ToDo提案元（Intrinsic / 他）が `load_quality_config` を用いていない。

### 1.2 Learning / RAG API が常時起動に含まれていない
- **現象**: 自動起動は **Intrinsic Score (5130)** と **Todo Queue (5134)** のみ。Learning System (5126) と RAG Memory (5103) は含まれていない。
- **影響**: 外部学習統合・夜間学習の Learning/RAG 連携、能力評価の Learning 参照が「接続拒否」でスキップされやすい。
- **該当**: `start_system3_services.ps1` / `setup_system3_autostart.ps1`。

### 1.3 API 呼び出しにリトライがない
- **現象**: 外部学習統合・夜間学習などで Learning/RAG/Score/Metrics への HTTP 呼び出しが1回失败すると即スキップ。一時的なネットワーク/起動遅延で学習が抜け落ちる。
- **影響**: 偶発的な API 障害で学習データの取り込み漏れが発生する。

### 1.4 Self-Assessment が固定的
- **現象**: ダッシュボードの「High noise / Low approval / Low execution」は汎用メッセージ。実メトリクス（N/A, 0% 等）に応じた**動的な説明や具体的アクション**がない。
- **影響**: 運用者が「次に何をすべきか」を判断しづらい。

### 1.5 Playbook メトリクスの取得が Markdown 依存
- **現象**: `playbook_auto_promotion` が日次/週次 Markdown をパースしてメトリクスを取得。フォーマット変更や欠損で壊れやすい。
- **影響**: 昇格判定が不安定になり、誤検知・見逃しのリスクがある。

### 1.6 品質改善バッチの定期実行がない
- **現象**: `todo_quality_improvement` の `update_quality_config_from_rejections` は手動実行用。**定期タスクとして登録されていない**（かつ 1.1 のとおり提案側未使用）。
- **影響**: 却下履歴に基づく設定更新が自動化されておらず、品質ループが回りにくい。

### 1.7 監視・アラートの未整備
- **現象**: 各 API の /health 監視、失敗時の通知（Slack 等）がなく、ログ確認に依存。
- **影響**: API 停止や連携失敗に気づくのが遅れやすい。

---

## 2. 強化ポイント（推奨アクション）

### 2.1 提案生成に `quality_config` を組み込む 【高】
- **内容**: タスク/ToDo 提案時に `todo_quality_improvement.load_quality_config()` を読み、`banned_tags` / `banned_categories` / `min_granularity` / `banned_time_ranges` でフィルタする。
- **例**: `intrinsic_motivation.generate_intrinsic_tasks()` 内で、生成したタスクの `category` / `tags` をチェックし、禁止と重なるものは除外。現在時刻が禁止時間帯なら提案しない。
- **効果**: 却下パターンを反映した提案になり、ノイズ低減・承認率向上が期待できる。

### 2.2 Learning / RAG を常時起動に含める 【高】
- **内容**: `start_system3_services.ps1` と `setup_system3_autostart.ps1` に **Learning System API**（`learning_system_api.py` 等・5126）と **RAG Memory API**（`rag_memory_enhanced.py` 等・5103）を追加する。
- **効果**: 外部学習統合・夜間学習・能力評価が常時利用可能になり、学習パイプラインが途切れにくくなる。

### 2.3 API 呼び出しのリトライ 【中】
- **内容**: 外部学習統合・夜間学習などの HTTP クライアントに、失敗時に指数バックオフで数回リトライする処理を入れる（例: 3回、1s / 2s / 4s）。
- **効果**: 一時的な API 不調や起動遅れでも、学習データの取り込み漏れを減らせる。

### 2.4 Self-Assessment の動的化 【中】
- **内容**: `create_system3_status` の Self-Assessment を、実メトリクス（approval / execution / noise の有無・大小）に応じて分岐させる。
  - 例: `approval_rate` が N/A または低い → 「提案粒度・優先度の見直し」「quality_config の利用」を推奨。
  - `execution_rate` が低い → 「承認後フロー・実行トリガーの確認」を推奨。
  - `noise_index` が高い → 「提案品質・上限の見直し」を推奨。
- **効果**: ダッシュボードから「次にやるべきこと」が分かりやすくなる。

### 2.5 品質改善バッチの定期実行 【中】
- **内容**: `python todo_quality_improvement.py`（`update_quality_config_from_rejections` 実行）を日次などでタスクスケジューラに登録。あわせて 2.1 を実施し、**提案側がその設定を参照する**ようにする。
- **効果**: 却下履歴に基づく設定更新が自動化され、品質ループが継続して回る。

### 2.6 監視・アラートの導入 【中】
- **内容**: 各 API の /health（または /api/score, /api/metrics 等）を定期的に叩き、失敗時はログに記録。任意で Slack 等に通知。
- **効果**: API 停止や連携失敗を早く検知できる。

### 2.7 Playbook メトリクス取得の堅牢化 【低〜中】
- **内容**: 可能なら Markdown スクレイピングに加え、**API や構造化データ（JSON 等）**からメトリクスを取得する経路を用意する。既存の Score / Todo メトリクス API の活用を検討。
- **効果**: フォーマット変更に強くなり、昇格判定の安定性が上がる。

### 2.8 デグラデッドモードの明示 【低】
- **内容**: Learning / RAG が落ちていても、Obsidian へのレポート保存などは継続し、統合だけ「後でリトライ」または「スキップしてレポートは残す」と明示する。
- **効果**: 一部 API 障害時でも、利用できる範囲の機能を継続でき、運用者の理解も得やすい。

---

## 3. 優先度の目安

| 優先度 | 項目 | 効果 |
|--------|------|------|
| 高 | 2.1 提案生成に quality_config 組み込み | 品質ループが完結し、ノイズ・低承認率の改善に直結 |
| 高 | 2.2 Learning / RAG を常時起動に追加 | 学習パイプライン全体の稼働率向上 |
| 中 | 2.3 API リトライ | 一時障害時の取り込み漏れ削減 |
| 中 | 2.4 Self-Assessment 動的化 | ダッシュボードの実用性向上 |
| 中 | 2.5 品質改善バッチの定期実行 | 品質ループの自動化（2.1 とセットで効果大） |
| 中 | 2.6 監視・アラート | 障害検知の迅速化 |
| 低〜中 | 2.7 Playbook メトリクス堅牢化 | 昇格判定の安定化 |
| 低 | 2.8 デグラデッドモード | 部分障害時の運用性向上 |

---

## 4. 実装メモ（2.1〜2.8）

| 項目 | 対応内容 |
|------|----------|
| 2.1 | `intrinsic_todo_queue.generate_proposals` で `load_quality_config` を読み、`_passes_quality_filter` で禁止タグ・カテゴリ・粒度・時間帯をフィルタ。`IntrinsicTodo.category` 追加。 |
| 2.2 | `start_system3_services.ps1` / `setup_system3_autostart.ps1` に Learning (5126)・RAG (5103) を追加。 |
| 2.3 | `system3_http_retry` で GET/POST リトライ。`system3_external_learning_integration`・`system3_learning_nightly` で利用。 |
| 2.4 | `create_system3_status` の Self-Assessment を実メトリクスに応じて出し分け（N/A/低/高でメッセージ変更）。 |
| 2.5 | `schedule_system3_todo_quality.ps1` で日次 04:00 に `todo_quality_improvement` を実行。 |
| 2.6 | `system3_health_check.py` で 4 API をチェックし `logs/system3_health_check.log` に記録。`schedule_system3_health_check.ps1` で 15 分ごと実行。 |
| 2.7 | `playbook_auto_promotion` で Markdown パースに try/except・範囲チェックを追加。不足時は Score/Todo API で補完。 |
| 2.8 | 外部学習統合で Learning/RAG 失敗時に「Degraded: レポートは保存済み、次回再試行」を明示。 |

---

## 5. 問題点・注意点（知っておくこと）

### 5.1 Learning / RAG の起動依存
- **常時起動**に Learning・RAG を追加したが、これらは **learning_system**（Mem0 等）や **rag_memory_enhanced**（Ollama 等）に依存する場合がある。
- 未設定・起動失敗時はログオン時にタスクが失敗する可能性がある。必要なら `setup_system3_autostart` で Learning/RAG を外すか、依存サービスの起動順・環境変数を整える。

### 5.2 品質フィルタの適用範囲
- **quality_config** を参照するのは **`intrinsic_todo_queue.generate_proposals`**（Todo 提案）と **`intrinsic_motivation.generate_intrinsic_tasks`**（内発タスク）の両方。
- 内発タスクも banned_categories・banned_time_ranges・min_granularity でフィルタされる（2026-01 実装済み）。

### 5.3 スケジュール登録
- `schedule_system3_todo_quality.ps1` と `schedule_system3_health_check.ps1` は **初回に手動で実行**するか、**`setup_system3_autostart.ps1 -IncludeScheduledTasks`** でまとめて登録可能（2026-01 実装済み）。

### 5.4 ヘルスチェックの通知
- 監視は **ログ出力**（`logs/system3_health_check.log`）＋ **Webhook**（`SYSTEM3_ALERT_WEBHOOK_URL` / `PHASE2_ALERT_WEBHOOK_URL` / `SLACK_WEBHOOK_URL` が設定されていれば失敗時に POST、2026-01 実装済み）。

### 5.5 Playbook の API フォールバック
- Markdown でメトリクスが不足しているときだけ Score/Todo API で補完する。**Playbook 単位**のメトリクスは API にないため、グローバルな Score/Todo で代用している。

---

## 6. 関連ファイル

- 品質ループ: `todo_quality_improvement.py`, `intrinsic_motivation.py`, `intrinsic_todo_queue.py`
- 常時起動: `start_system3_services.ps1`, `setup_system3_autostart.ps1`
- 外部学習統合: `system3_external_learning.py`, `system3_external_learning_integration.py`
- 夜間学習: `system3_learning_nightly.py`
- ステータス・Self-Assessment: `create_system3_status.py`
- Playbook 昇格: `playbook_auto_promotion.py`
- リトライ: `system3_http_retry.py`
- ヘルスチェック: `system3_health_check.py`, `schedule_system3_health_check.ps1`
- 品質スケジュール: `schedule_system3_todo_quality.ps1`
