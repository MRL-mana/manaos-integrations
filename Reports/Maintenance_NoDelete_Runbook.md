# Maintenance Runbook (No Delete)

## 目的

- 破壊的変更なしで、母艦とまなOSの健全性・容量・差分を棚卸しする。

## 実行手順

1. サービス健全性の確認
   - タスク: ManaOS: サービスヘルスチェック
2. 自動応答の確認
   - タスク: ManaOS: auto-local 応答テスト
3. Tool Server 統合確認
   - タスク: ManaOS: Tool Server統合テスト
4. ドライラン棚卸しレポート生成
   - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\maintenance_inventory_dryrun.ps1`

## 判定ルール

- Coreサービスが全てOKなら運用継続可能。
- Optional系（例: ComfyUI/OpenWebUI）は、未起動時は「要否確認」に分類し障害扱いしない。
- Git差分は「運用設定」「機能改修」「実験/一時ファイル」に分類する。

## Git差分の整理（運用設定だけ先にまとめる）

1. 運用設定・レポート系だけを先に確認する
   - 例: `.vscode/tasks.json`, `Reports/*.md`, `Reports/*.txt`, `phase1_metrics_snapshot.json`
2. 機能改修は別枠でまとめる
   - 例: `unified_api_server.py`, `tool_server/main.py`, `*_integration.py`
3. 新規ツール・ドキュメントは最後に
   - 例: `docs/IMAGE_GENERATION_GUIDE.md`, `scripts/generate_image_cli.py`
4. 分類が終わるまで削除・移動はしない

## 出力物

- `Reports/Maintenance_Inventory_YYYY-MM-DD.md`（手動棚卸し）
- `Reports/Maintenance_DryRun_*.md`（自動ドライラン）
- `Reports/CleanupCandidates_*.txt`（削除候補一覧・実行なし）

## 注意

- 本Runbookは削除・移動・圧縮を実行しない。
- 実削除フェーズに入る場合は、候補一覧をレビューしてから別手順で実施する。
