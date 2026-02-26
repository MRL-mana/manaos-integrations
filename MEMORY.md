# ManaOS メモリ

> このファイルはエージェントの長期記憶として機能します。
> 手動編集 OK。RLAnything セクションは自動更新されます。

## プロジェクト概要

- **ManaOS**: 個人向け統合 AI オペレーティングシステム
- **リポジトリ**: manaos-integrations (Python 3.10 / FastAPI / Obsidian / MCP)
- **バックエンド**: manaos-rpg (port 9510)

## 自己進化システム

RLAnything フレームワーク (Princeton "RLAnything" 論文ベース) により、
Policy（行動）・Reward（採点）・Environment（難易度）を同時最適化。

- 観測 → フィードバック → スキル抽出 の 3 フェーズで自動学習
- 成功率 80% を目標に難易度を自動調整（カリキュラム学習）
- 学習済みスキルは下記セクションに自動追記

<!-- rl_anything:start -->
## RLAnything 自己進化メモ

更新日時: 2026-02-26 14:50
現在の難易度: **standard**
蓄積スキル: 5 件

### 学習済みスキル (成功パターン)

1. **段階的実装** (成功率: 100%, n=2)
   - 3-10 ステップの適度な粒度でタスクを分割して実行
   - タグ: incremental, stepwise

2. **ツール連携: read_file → run_test** (成功率: 100%, n=2)
   - 「read_file → run_test」の順でツールを使用するパターン (n=2)
   - タグ: tool-chain

3. **ツール連携: run_test → create_file** (成功率: 100%, n=2)
   - 「run_test → create_file」の順でツールを使用するパターン (n=2)
   - タグ: tool-chain

4. **事前調査パターン** (成功率: 75%, n=4)
   - コード変更前にファイル読み込み/検索で十分なコンテキストを取得
   - タグ: research, context-gathering

5. **ツール連携: read_file → create_file** (成功率: 50%, n=2)
   - 「read_file → create_file」の順でツールを使用するパターン (n=2)
   - タグ: tool-chain

### 推奨行動指針

標準: 目的を示し、実装方法はエージェント判断。例: 「日付処理の国際化対応をして」

<!-- rl_anything:end -->
