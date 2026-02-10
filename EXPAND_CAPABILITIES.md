# ManaOS 機能拡張プラン

目的: VSCode/Cursor と ManaOS の連携範囲を拡張し、記憶・学習・補完品質を向上させる。

短期 (今すぐ)
- Mem0 連携を追加（`add_mem0_integration.py` を実行）
- Obsidian 連携設計（メモの同期・検索）
- VSCode 側でメモリ対応フックを有効化（設定更新 / 拡張フック）

中期
- Cursor のメモリ優先補完ロジックを有効化
- 自動統合テスト（記憶の保存/検索/反映）
- CI用の簡易テストスクリプト追加

長期
- 監視ダッシュボード（Prometheus/Grafana 連携）
- 高度な学習ポリシー（昇格・再練習パイプライン）

実行コマンド例:

```powershell
# Mem0 を設定に追加
python add_mem0_integration.py

# すべてのサービスを起動 (VSCode タスクからも可)
python start_vscode_cursor_services.py

# 統合テストを実行
python test_vscode_integration.py
```

次のアクション候補:
1. `add_mem0_integration.py` を実行して設定へ登録
2. Obsidian 連携の具体設計を作成
3. VSCode 拡張フックの実装を開始

ご希望を教えてください（例: 1 を実行して下さい）。
