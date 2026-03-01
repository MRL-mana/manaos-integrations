# ManaOS Integrations

**v2.6.0** — ManaOS統合サービスシステム

VSCode/Cursorに接続するメモリベースAIアシスタント。ManaOS と外部サービス（ComfyUI / Google Drive / CivitAI / n8n / Slack / Voice など）をつなぐ統合リポジトリ。

---

## 🚀 公式ルート（最小構成）

ManaOSは「Unified APIを入口とする統合基盤」です。  
まずは以下の4サービスのみを起動してください。

### 必須（コア）

- Memory
- Learning
- LLM Routing
- Unified API（統合入口）

この4つが動けば、ManaOSは成立します。

---

## ➕ 任意追加（必要時のみ有効化）

以下は用途が発生した場合のみ有効化します。

- Windows Automation
- Pico HID
- Moltbot
- ComfyUI
- Gallery

常時起動は推奨しません。

---

## 🏭 本番推奨構成

- Waitress運用
- 3段階キー（Admin / Ops / Read-only）
- IP allow/block
- Rate limit
- 監査ログ有効化

---

## 🛣 最短起動手順（一本道）

### Step 1

必須4サービスを起動

### Step 2

Unified APIヘルス確認

### Step 3

サンプル1リクエスト実行

### Step 4

失敗時は「[トラブルシューティング](TROUBLESHOOTING.md)」へ

一本道以外から始めないこと。

最短起動（VSCode/Cursor）:

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: すべてのサービスを起動"
```

ヘルスチェック:

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: サービスヘルスチェック"
```

---

## 📘 Single Source of Truth

- ポート番号
- サービスURL
- 依存関係
- 有効/無効フラグ

これらは **`config/services_ledger.yaml` のみを正** とします。  
READMEには重複記載しません。

---

## 📂 ディレクトリ運用ルール

| ディレクトリ | 用途 |
|---|---|
| active | 現行運用中 |
| experiments | 検証中 |
| archive | 過去資産（読取専用） |

---

## 🏗 アーキテクチャ概要

サービス間の役割・接続・依存は `config/services_ledger.yaml` を参照してください。

メモリアーキテクチャ:

```
ユーザー入力
  ├── MRLMemoryExtractor（固有名詞・数値・TODO抽出）
  │     └── Scratchpad → Working Memory → Long-term (Obsidian)
  ├── RAG Memory V2（SQLite + Ollama embeddings）
  └── Learning System（行動パターン学習＋自動最適化提案）
```

---

## 🧪 テスト

```bash
# 全テスト実行（124テスト）
python -m pytest tests/ --tb=short

# カバレッジ付き
python -m pytest tests/ --cov=. --cov-report=term-missing
```

テスト対象:
- `test_mrl_memory.py` — MRL Memory 抽出・Scratchpad・並行書き込み（13テスト）
- `test_learning_system.py` — 学習記録・永続化・自動最適化（14テスト）
- `test_health_check.py` — ヘルスチェック・設定検証（18テスト）
- `test_manaos_logger.py` — 統合ロガー（7テスト）
- `test_gpu_resource_manager.py` — GPU非同期管理（8テスト）
- `test_windows_automation.py` — Windows自動化ツールキット（14テスト）
- `test_pico_hid.py` — Pico HID / pynput マウス・キーボード（13テスト）

---

## CI Gates

### CI Contract Gate (Stage2)

This repo enforces **Stage2 Contract Checks** as a required CI gate.

**What it checks**

- `tools/validate_contract.py --strict` verifies a small set of **stable, read-only** endpoints and their minimal JSON contract.

**When CI fails**

- A failure usually means an API contract changed (response shape / auth requirement / endpoint behavior).
- Do **not** weaken the gate. Update the contract intentionally.

**How to update the contract (1 PR rule)**

1. Update the API implementation (or routing) as needed.
2. Update `tools/validate_contract.py` to match the intended new contract.
3. Ensure CI passes with `--strict` in the same PR.
4. In the PR description, write a one-line rationale: `contract update: <why>`.

**Notes**

- Stage2 is designed to stay **read-only and low-dependency**.
- If an endpoint requires elevated privileges (ops/admin) or external dependencies, keep it out of Stage2 and create a separate optional gate.

---

## 📝 ロギング

全コアモジュールは `manaos_logger.get_logger(__name__)` で統一されたロガーを使用:
- **RotatingFileHandler**: `logs/` 配下に自動ローテーション（10MB × 5世代）
- **コンソール出力**: 構造化フォーマット
- **try/except フォールバック**: `manaos_logger` が利用不可の場合は標準 `logging.getLogger` にフォールバック

---

## 詳細ドキュメント

### 基本ガイド
- **[クイックリファレンス](QUICKREF.md)** - 1ページのチートシート
- **[Pixel7 5分セキュア導線](docs/guides/PIXEL7_MINIMAL_SECURE_MODE.md)** - 安全デフォルトでの起動・確認・CLI運用
- **[VSCodeセットアップ](VSCODE_SETUP_GUIDE.md)** - VSCode完全セットアップガイド
- **[VSCode vs Cursor](VSCODE_VS_CURSOR.md)** - どっちを使うべき?比較ガイド
- **[VSCodeチェックリスト](VSCODE_CHECKLIST.md)** - 対応状況とクイックガイド
- **[起動ガイド](STARTUP_GUIDE.md)** - 詳細な起動手順
- **[System3ガイド](SYSTEM3_GUIDE.md)** - 自律運用システム
- **[緊急停止ガイド](EMERGENCY_STOP_GUIDE.md)** - 緊急停止方法

### 環境設定・デプロイメント
- **[環境変数設定ガイド](ENVIRONMENT_VARIABLES.md)** - サービスURL/ポート設定の完全ガイド
- **[トラブルシューティング](TROUBLESHOOTING.md)** - よくある問題と解決方法
- **[完全デプロイメントガイド](COMPLETE_DEPLOYMENT_GUIDE.md)** - 全シナリオ統合ガイド（ローカル/Docker/Kubernetes）
- **[分散デプロイメント](DISTRIBUTED_DEPLOYMENT.md)** - 複数デバイス間でのサービス分散実行
- **[Dockerデプロイメント](DOCKER_DEPLOYMENT.md)** - Docker/Docker Composeでのコンテナ実行ガイド
- **[Kubernetesデプロイメント](KUBERNETES_DEPLOYMENT.md)** - Kubernetes/Helmでのクラウドデプロイガイド
- **[ArgoCD GitOpsガイド](ARGOCD_GITOPS_GUIDE.md)** - GitOpsによる自動デプロイメント
- **[エンタープライズセキュリティ＆オブザーバビリティ](ENTERPRISE_SECURITY_OBSERVABILITY_GUIDE.md)** - 本番環境向けセキュリティ強化・バックアップ・監視の総合ガイド

### MCP・セキュリティ
- **[MCPサーバーガイド](docs/guides/MCP_SERVERS_GUIDE.md)** - MCP設定と使い方
- **[セキュリティ](docs/guides/SECURITY_HARDENING.md)** - API認証・ハードニング

### Kubernetesエンタープライズ機能
- **[Pod Security Standards](kubernetes/security/pod-security-standards.yaml)** - Pod セキュリティ標準（Restricted/Baseline）
- **[Network Policies](kubernetes/security/network-policies.yaml)** - ゼロトラスト・マイクロセグメンテーション
- **[RBAC & ServiceAccounts](kubernetes/security/rbac-service-accounts.yaml)** - 最小権限の原則に基づくロール管理
- **[セキュリティスキャン自動化](kubernetes/security/security-scanning.yaml)** - SAST/依存関係/コンテナスキャン

### バックアップ・災害対策
- **[Velero バックアップ設定](kubernetes/backup/velero-config.yaml)** - 自動バックアップ・DR手順

### オブザーバビリティ
- **[Jaeger 分散トレーシング](kubernetes/observability/jaeger-tracing.yaml)** - マイクロサービス間のリクエストフロー可視化
- **[Loki ログ集約](kubernetes/observability/loki-logging.yaml)** - Grafana Loki によるログ管理

### テスト・品質保証
- **[テストガイド](TESTING_GUIDE.md)** - ユニット/統合/E2Eテストの実行方法
- **[テスト実行スクリプト](run_tests.ps1)** - 簡単なテスト実行用PowerShellスクリプト

---

## 重要（セキュリティ）

- **統合APIサーバー**: `run_unified_api_server_prod.py`（本番）
- **最小ハードニング手順**: `docs/guides/SECURITY_HARDENING.md`
  - 3段階キー（Admin / Ops / Read-only）
  - IP allow/block、CORS制御
  - 監査ログ、Confirm Token、Rate limit / Concurrency
  - OpenAPI公開制御、セキュリティヘッダ

## 起動

### クイックスタート（MCP・秘書ファイル整理）

統合API (9502) と MoltBot Gateway (8088) をまとめて起動する場合:

```bat
start_unified_api_and_moltbot.bat
```

疎通確認: `scripts\check_manaos_stack.bat`（拡張: `.\scripts\check_manaos_stack.ps1 -Extended`）。.env に `MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088` を設定すると MCP から秘書ファイル整理が利用可能。**よく使う起動・確認一覧**: [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)

### 開発（ローカル）

```bash
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: すべてのサービスを起動"
```

### 本番（推奨: Waitress）

```bat
start_unified_api_server_prod.bat
```

## 依存関係

- 最小: `requirements-core.txt`
- 開発: `requirements-dev.txt`（pytest, pytest-asyncio, mypy 等）
- 全部入り: `requirements.txt`

## MCPサーバー

- **MCP本体**: `manaos_unified_mcp_server/server.py`
- **一括登録**: `.\add_all_mcp_servers_to_cursor.ps1`（プロジェクトルートで実行、パスは自動取得）
- **詳細**: [docs/guides/MCP_SERVERS_GUIDE.md](docs/guides/MCP_SERVERS_GUIDE.md)
- **Skills と MCP の使い分け**: [docs/guides/SKILLS_AND_MCP_GUIDE.md](docs/guides/SKILLS_AND_MCP_GUIDE.md)
- **起動依存関係**: [docs/guides/STARTUP_DEPENDENCY.md](docs/guides/STARTUP_DEPENDENCY.md)

## スクリプト整理

`scripts/CATALOG.md` にルート配下のスクリプト一覧がカテゴリ別に整理されています。カタログ更新:

```bash
python scripts/catalog_scripts.py > scripts/CATALOG.md
```

Pixel7 最小CLI（health/status/open-url）は `scripts/pixel7/manaos_pixel7_cli.py` を使用します。

## Dashboard監視運用メモ

- 監視の証跡は `logs/dashboard_alert.log`（通知は補助）
- 更新タスク: `\ManaOS_Dashboard_Update`
- アラートタスク: `\ManaOS_Dashboard_Alert`

疎通確認（手動Run → ログ確認）:

```powershell
schtasks /Run /TN "ManaOS_Dashboard_Update"
schtasks /Run /TN "ManaOS_Dashboard_Alert"
Get-Content .\logs\dashboard_alert.log -Tail 50
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\check_file_secretary_fail_streak.ps1 -FailThreshold 3 -Strict
```
