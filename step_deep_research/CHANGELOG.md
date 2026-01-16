# Changelog

All notable changes to Step-Deep-Research will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.4.0] - 2025-01-28

### Added - 価値フェーズ

- **専門テンプレート3本**: 技術選定/トラブル調査/最新動向チェック
- **テンプレート自動選択**: Template Routerによるクエリからの自動検出
- **1分チェック**: 完成度確認の自動化スクリプト

### Changed

- Writer: テンプレートタイプに応じた動的コンテンツ生成
- Orchestrator: ユーザークエリをWriterに渡すように変更

---

## [1.3.0] - 2025-01-28

### Added - 長期安定稼働仕上げ

- **フェイルセーフガード**: 連続失敗時の早期終了と部分レポート生成
- **キャッシュシステム**: 同一クエリの再調査防止（TTL 7日）
- **ソース品質フィルタ**: 一次情報優先、まとめサイト補助扱い
- **回帰テスト**: 10問セット（ManaOS用途：RDP/自動化/LLM運用/セキュリティ）
- **自動逆算データパイプライン**: 高得点レポートから学習データ自動生成
- **メトリクスダッシュボード**: 完成度チェック指標の可視化

### Changed

- Orchestrator: キャッシュチェックとフェイルセーフ統合
- Research Loop: フェイルセーフガード統合
- Searcher: ソース品質フィルタ統合
- Reader: ソース品質フィルタ統合

---

## [1.2.0] - 2025-01-28

### Added - 運用ガード実装

- **予算ガード**: コスト爆発防止（max_iterations, max_search_calls, max_sources, time_budget_sec, token_budget）
- **Critic Guard**: 機械的品質検証（引用の十分性、結論-証拠リンク、反証チェック、事実/推論区別）
- **引用フォーマッター**: 強制引用フォーマット（Claim-ID、必須セクション、自動参考文献）

### Changed

- Orchestrator: `spent_budget`と`stop_reason`を返すように変更
- Critic: `citations`パラメータ追加、Critic Guard統合
- Writer: Citation Formatter統合

### Fixed

- 型エラー修正（Citation型ヒント追加）

---

## [1.1.0] - 2025-01-28

### Added - 統合・テスト

- **Trinity統合**: Remi/Luna/Mina役割分担とログ記録
- **逆算データ生成**: 高得点レポートから学習データ生成
- **統合テスト**: ManaOSサービスとの連携確認
- **APIサーバー**: Flask APIサーバー実装
- **サービス統合**: Intent Router / Service Monitor統合スクリプト

### Changed

- Orchestrator: Trinity統合、逆算データ生成統合

---

## [1.0.0] - 2025-01-28

### Added - 初回リリース

- **Orchestrator**: メイン制御システム
- **Planner**: 計画立案エージェント
- **Research Loop**: 検索→読解→検証ループ
  - Searcher: 検索エージェント
  - Reader: 読解・引用抽出エージェント
  - Verifier: 検証・反証探索エージェント
- **Writer**: レポート生成エージェント
- **Critic**: 品質評価エージェント（30項目ルーブリック）
- **データスキーマ**: 全コンポーネントのデータ構造定義
- **プロンプトテンプレート**: Planner/Reader/Verifier/Writer/Critic/Revision
- **レポートテンプレート**: 標準レポートフォーマット
- **ルーブリック**: 20項目→30項目

### Features

- 行動学習ベースの調査システム
- 機械的品質評価（ルーブリック）
- 包括的ログ記録（JSONL形式）
- ManaOS統合（manaos_logger, manaos_error_handler, llm_optimization）

---

## [Unreleased]

### Planned

- Critic二段化（構造×内容）
- 失敗ログから自動カリキュラム再生成
- 社内ナレッジ統合強化
- カスタムテンプレート追加機能
- ダッシュボード可視化改善

---

## バージョン履歴

- **v1.4.0**: 価値フェーズ（専門テンプレート、1分チェック）
- **v1.3.0**: 長期安定稼働仕上げ（フェイルセーフ、キャッシュ、ソース品質、回帰テスト、逆算データ、メトリクス）
- **v1.2.0**: 運用ガード実装（予算ガード、Critic Guard、引用フォーマッター）
- **v1.1.0**: 統合・テスト（Trinity、逆算データ、API、統合テスト）
- **v1.0.0**: 初回リリース（コア機能実装）

---

## セマンティックバージョニング

- **MAJOR** (x.0.0): 破壊的変更
- **MINOR** (0.x.0): 新機能追加（後方互換性あり）
- **PATCH** (0.0.x): バグ修正（後方互換性あり）

---

**ManaOS Step-Deep-Research** - 専門調査員AI

