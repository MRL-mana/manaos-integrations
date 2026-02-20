# ManaOS メンテナンス・棚卸しレポート

- 実施日: 2026-02-20
- 対象: 母艦 (Windows) + manaos_integrations
- 方針: まずは可観測化（ヘルス/統合/容量）を実施し、削除系はドライラン前提で段階実施

## 1) 並列診断サマリー

### サービスヘルス
- Core: 6/6 稼働
  - MRL Memory, Learning System, LLM Routing, OpenAI Router, Unified API, Video Pipeline は正常
- Infra/Optional: 4/6 稼働
  - NG: ComfyUI (8188), Moltbot Gateway (8088) は未起動/接続拒否

### 統合テスト
- Tool Server 統合テスト: 6/8 成功
- 成功: health/openapi/service_status/execute_command/vscode_open_file/command_policy
- 失敗: ComfyUI 接続, OpenWebUI 接続（いずれも接続拒否）

### LLM auto-local 応答テスト
- OpenAI互換 Router (5211) 稼働確認
- モデル: `llama3-uncensored:latest`
- 応答取得: OK

## 2) 母艦リソース確認

- CPU: AMD Ryzen 7 9700X (8C/16T)
- RAM: 125.7 GB
- GPU: NVIDIA GeForce RTX 5080
- 稼働時間: 約60時間

## 3) 容量棚卸し（Desktop上位）

1. 画像評価整理: 92.69 GB
2. backups: 68.75 GB
3. .tmp.driveupload: 19.30 GB
4. migrated_from_konoha: 9.39 GB
5. manaos_integrations: 5.67 GB
6. .venv_gpu: 4.76 GB
7. data: 3.55 GB
8. 大曲: 2.96 GB

## 4) ログ棚卸し（manaos_integrations/logs 上位）

- 10MB級ローテーションログが多数存在（`*.log.1`, `*.log.5`）
- 代表:
  - `notification_hub.log.5` 10.0 MB
  - `memory_unified.log.5` 10.0 MB
  - `manaos_core_api.log.5` 10.0 MB
  - `__main__.log` 7.81 MB
  - `Integration.Mem0.log` 3.65 MB

## 5) Git作業棚卸し（未コミット）

- 変更あり（抜粋）:
  - `.vscode/tasks.json`
  - `tool_server/main.py`
  - `unified_api_server.py`
  - `unified_api_mcp_server/server.py`
  - `gallery_api_mcp_server/server.py`
- 未追跡（抜粋）:
  - `docs/IMAGE_GENERATION_GUIDE.md`
  - `scripts/generate_image_cli.py`
  - `google_calendar_tasks_sheets_integration.py`

## 5.1) Git差分分類（暫定）

### 運用設定・レポート系
- `.vscode/tasks.json`
- `Reports/OpenWebUI_Acceptance_Latest_Status.txt`
- `phase1_metrics_snapshot.json`
- `Reports/Maintenance_Inventory_2026-02-20.md`
- `Reports/Maintenance_NoDelete_Runbook.md`
- `Reports/CleanupCandidates_Logs_2026-02-20.txt`
- `Reports/CleanupCandidates_DriveTmp_2026-02-20.txt`

### 機能改修・統合改善
- `gallery_api_mcp_server/server.py`
- `tool_server/main.py`
- `unified_api_mcp_server/server.py`
- `unified_api_server.py`
- `manaos_core_api.py`
- `mem0_integration.py`
- `google_drive_integration.py`
- `vscode_cursor_integration.py`
- `ensure_optional_services.ps1`
- `run_manaos_full_smoke.ps1`
- `tests/integration/test_tool_server_integration.py`
- `check_unconfigured.py`

### 新規ツール・ドキュメント
- `docs/IMAGE_GENERATION_GUIDE.md`
- `scripts/generate_image_cli.py`
- `scripts/maintenance_inventory_dryrun.ps1`
- `google_calendar_tasks_sheets_integration.py`
- `reauthenticate_google_api.py`

## 6) 推奨アクション（安全順）

### A. 即実施（低リスク）
1. Optional系の起動ポリシーを明確化（ComfyUI/OpenWebUIを常時対象にするか明記）
2. ログローテーション保持数の見直し（`*.log.5` の保持期間/世代を削減）
3. 長時間稼働後の軽い再起動ウィンドウ確保（メモリ断片化予防）

### B. 本日中（中リスク）
1. `backups`, `.tmp.driveupload`, `画像評価整理` の重複・陳腐化データをドライラン抽出
2. `manaos_integrations/logs` の古いローテーションログを日付条件でアーカイブ or 削除
3. Git差分を「運用変更」「実験」「ドキュメント」に3分類

### C. 週次化（運用定着）
1. 週次ヘルスチェック自動実行
2. 週次容量レポート（上位10フォルダ）
3. 週次ログ圧縮/削除の自動化

## 7) GPU活用メモ

- GPU (RTX 5080) は利用可能状態。
- 本日の作業（ヘルス/統合/棚卸し）は主にI/O・ネットワーク中心のためGPU寄与は限定的。
- 画像生成・推論系はGPUワークロードとして別ジョブで並列化可能。
