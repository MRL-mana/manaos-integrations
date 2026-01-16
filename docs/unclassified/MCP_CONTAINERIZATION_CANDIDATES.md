# MCPサーバー化・コンテナ化候補リスト

**作成日**: 2025-01-28  
**目的**: ManaOS統合サービスの中で、MCPサーバー化やコンテナ化すべき候補を整理

---

## 📊 現状分析

### 既存のMCPサーバー
- ✅ `manaos_unified_mcp_server` - 統合MCPサーバー
- ✅ `llm_routing_mcp_server` - LLMルーティングMCP
- ✅ `n8n_mcp_server` - n8nワークフローMCP
- ✅ `svi_mcp_server` - SVI画像生成MCP
- ✅ `konoha_mcp_servers/manaos_unified_system_mcp` - 統合システムMCP（Docker化済み）

### 既存のDocker設定
- ✅ `docker-compose.always-ready-llm.yml` - LLM関連サービス
- ✅ `docker-compose.searxng.yml` - SearXNG検索エンジン
- ✅ `konoha_mcp_servers/manaos_unified_system_mcp/docker-compose.yml` - RunPod MCP

---

## 🎯 MCPサーバー化推奨候補

### 🔴 優先度: 高（すぐにMCPサーバー化すべき）

#### 1. **Unified API Server** (ポート9500)
- **ファイル**: `unified_api_server.py`
- **理由**: 
  - すべての外部システム統合を管理するコアAPI
  - 多くのエンドポイントを持つ（ComfyUI、Google Drive、CivitAI等）
  - MCPサーバー化により、CursorやClaude Desktopから直接利用可能
- **メリット**: 
  - 統合APIへの統一アクセス
  - ツールとしての再利用性向上
- **実装難易度**: 中

#### 2. **LLM Routing API** (ポート未設定)
- **ファイル**: `llm_routing.py`, `manaos_llm_routing_api.py`
- **理由**:
  - LLMルーティング機能は既にMCPサーバー化されているが、APIサーバー版も存在
  - API版をMCPサーバーとしても公開することで、柔軟な利用が可能
- **メリット**:
  - HTTP APIとMCPの両方から利用可能
- **実装難易度**: 低（既存のMCPサーバーを拡張）

#### 3. **Step Deep Research Service** (ポート5121)
- **ファイル**: `step_deep_research_service.py`
- **理由**:
  - 深いリサーチ機能を提供する重要なサービス
  - MCPサーバー化により、AIアシスタントから直接リサーチタスクを実行可能
- **メリット**:
  - リサーチ機能の再利用性向上
  - AIアシスタントとの統合強化
- **実装難易度**: 中

#### 4. **Gallery API Server** (ポート5559)
- **ファイル**: `gallery_api_server.py`
- **理由**:
  - 画像生成・管理API
  - MCPサーバー化により、画像生成機能をツールとして提供可能
- **メリット**:
  - 画像生成機能の統一アクセス
  - 既存のSVI MCPサーバーとの統合可能性
- **実装難易度**: 中

### 🟡 優先度: 中（検討すべき）

#### 5. **System Status API** (ポート5112)
- **ファイル**: `system_status_api.py`
- **理由**:
  - 全サービスのステータスを監視
  - MCPサーバー化により、システム状態をAIアシスタントから確認可能
- **メリット**:
  - システム監視の自動化
- **実装難易度**: 低

#### 6. **SSOT API** (ポート5120)
- **ファイル**: `ssot_api.py`
- **理由**:
  - Single Source of Truth API
  - 設定やデータの一元管理
- **メリット**:
  - 設定管理の統一アクセス
- **実装難易度**: 低

#### 7. **Service Monitor** (ポート5111)
- **ファイル**: `service_monitor.py`
- **理由**:
  - サービス監視機能
  - MCPサーバー化により、監視機能をツールとして提供可能
- **メリット**:
  - 監視機能の自動化
- **実装難易度**: 低

### 🟢 優先度: 低（将来的に検討）

#### 8. **Core Services** (ポート5100-5110)
- Intent Router, Task Planner, Task Critic, RAG Memory等
- **理由**:
  - 内部サービスとして動作している
  - 直接MCPサーバー化するより、統合API経由でアクセスする方が適切
- **推奨**: Unified API Server経由でアクセス

---

## 🐳 コンテナ化推奨候補

### 🔴 優先度: 高（すぐにコンテナ化すべき）

#### 1. **Unified API Server** (ポート9500)
- **理由**:
  - コアAPIサーバーとして常時起動が必要
  - コンテナ化により、環境依存を排除し、デプロイが容易に
- **メリット**:
  - 環境の統一
  - スケーラビリティの向上
  - 依存関係の管理が容易
- **実装難易度**: 中

#### 2. **Step Deep Research Service** (ポート5121)
- **理由**:
  - 独立したサービスとして動作
  - コンテナ化により、リソース管理が容易に
- **メリット**:
  - リソース制限の設定が容易
  - 他のサービスへの影響を分離
- **実装難易度**: 中

#### 3. **Gallery API Server** (ポート5559)
- **理由**:
  - 画像生成サービスとして独立動作
  - GPUリソースが必要な場合がある
- **メリット**:
  - GPUリソースの分離管理
  - 画像生成処理の分離
- **実装難易度**: 中

### 🟡 優先度: 中（検討すべき）

#### 4. **LLM Routing API**
- **理由**:
  - LLMルーティング機能の独立運用
- **メリット**:
  - LLM関連処理の分離
- **実装難易度**: 低

#### 5. **Core Services群** (ポート5100-5110)
- **理由**:
  - 複数のサービスをまとめてコンテナ化
- **メリット**:
  - 一括管理が容易
  - リソース制限の設定
- **実装難易度**: 高（複数サービスを統合）

---

## 📋 実装推奨順序

### Phase 1: 高優先度MCPサーバー化（1-2週間）
1. ✅ Unified API Server のMCPサーバー化
2. ✅ Step Deep Research Service のMCPサーバー化
3. ✅ Gallery API Server のMCPサーバー化

### Phase 2: 高優先度コンテナ化（2-3週間）
1. ✅ Unified API Server のコンテナ化
2. ✅ Step Deep Research Service のコンテナ化
3. ✅ Gallery API Server のコンテナ化

### Phase 3: 中優先度（1-2週間）
1. ✅ System Status API のMCPサーバー化
2. ✅ SSOT API のMCPサーバー化
3. ✅ Service Monitor のMCPサーバー化

---

## 🛠️ 実装時の考慮事項

### MCPサーバー化
- **標準化**: 既存のMCPサーバー（`manaos_unified_mcp_server`）のパターンを参考にする
- **ツール設計**: 各APIのエンドポイントをMCPツールとして適切に設計
- **エラーハンドリング**: 統一されたエラーハンドリングを実装
- **認証**: APIキーや認証情報の安全な管理

### コンテナ化
- **Dockerfile**: 軽量なベースイメージを使用（python:3.11-slim等）
- **docker-compose.yml**: 既存の設定を参考にする
- **環境変数**: 設定を環境変数で管理
- **ボリューム**: データ永続化のためのボリューム設定
- **ヘルスチェック**: 適切なヘルスチェックを実装
- **リソース制限**: メモリやCPUの制限を設定

### 統合
- **既存MCPサーバーとの統合**: 既存のMCPサーバーと統合可能な設計
- **APIとの互換性**: HTTP APIとMCPの両方から利用可能にする
- **ドキュメント**: 使用方法のドキュメントを作成

---

## 📝 次のステップ

1. **優先度の確認**: このリストをレビューし、優先度を調整
2. **実装計画**: Phase 1から順に実装を開始
3. **テンプレート作成**: MCPサーバー化とコンテナ化のテンプレートを作成
4. **テスト**: 各実装後に十分なテストを実施
5. **ドキュメント**: 使用方法と設定方法のドキュメントを作成

---

## 🔗 参考リソース

- 既存MCPサーバー: `konoha_mcp_servers/manaos_unified_system_mcp/`
- 既存Docker設定: `docker-compose.always-ready-llm.yml`
- サービス一覧: `service_monitor_config.json`
