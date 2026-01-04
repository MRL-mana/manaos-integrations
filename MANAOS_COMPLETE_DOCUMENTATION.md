# ManaOS 完全実装ドキュメント

**最終更新**: 2025-01-28  
**バージョン**: 1.0.0  
**状態**: 完全実装・動作確認済み・自動起動設定済み

---

## 📋 目次

1. [概要](#概要)
2. [システムアーキテクチャ](#システムアーキテクチャ)
3. [実装済み機能一覧](#実装済み機能一覧)
4. [各サービスの詳細](#各サービスの詳細)
5. [インストール・セットアップ](#インストールセットアップ)
6. [使用方法](#使用方法)
7. [API仕様](#api仕様)
8. [設定ファイル](#設定ファイル)
9. [トラブルシューティング](#トラブルシューティング)
10. [今後の拡張ポイント](#今後の拡張ポイント)

---

## 📖 概要

ManaOSは、「もう一人のマナ」を実現するための統合AIシステムです。思考・判断・実行・評価のサイクルを自動化し、ユーザーの意図を理解して適切なアクションを実行します。

### 主な特徴

- **思考AI**: 意図分類・計画作成・結果評価
- **記憶AI**: 重要度スコア・重複チェック・時系列メモリ
- **実行AI**: n8n/API/スクリプト/コマンド実行
- **統合AI**: エンドツーエンドの自動実行フロー
- **最適化AI**: GPU効率化・モデル選択・フィルタ機能

---

## 🏗️ システムアーキテクチャ

### 全体フロー

```
ユーザー入力（音声/テキスト/イベント）
  ↓
[LLM最適化 (5110)] - フィルタ・モデル選択
  ↓
[Intent Router (5100)] - 意図分類
  ↓
[Task Planner (5101)] - 実行計画作成
  ↓
[Task Queue (5104)] - キューに追加（Priority制御・Rate Limit）
  ↓
[Executor Enhanced (5107)] - タスク実行
  ├─ n8nワークフロー実行
  ├─ API呼び出し
  ├─ スクリプト実行
  └─ コマンド実行
  ↓
[Task Critic (5102)] - 結果評価
  ↓
[RAG Memory (5103)] - 記憶保存（重要度・重複チェック・時系列）
  ↓
[Content Generation (5109)] - 成果物自動生成（オプション）
  ↓
[UI Operations (5105)] - 結果表示・コスト追跡
  ↓
[Unified Orchestrator (5106)] - 全体統合
  ↓
[Portal Integration (5108)] - UI統合
```

### サービス間の連携

```
Unified Orchestrator (5106)
  ├─ Intent Router (5100)
  ├─ Task Planner (5101)
  ├─ Task Critic (5102)
  ├─ Task Queue (5104)
  ├─ Executor Enhanced (5107)
  └─ RAG Memory (5103)

Portal Integration (5108)
  ├─ Unified Orchestrator (5106)
  ├─ UI Operations (5105)
  └─ Task Queue (5104)

Service Monitor (5111)
  └─ 全サービス監視
```

---

## ✅ 実装済み機能一覧

### 🔥 優先度S：別次元に入る機能（4/4完了）

| # | 機能 | ポート | 状態 | 説明 |
|---|------|--------|------|------|
| 1 | Intent Router | 5100 | ✅ | ユーザー入力から意図を分類する軽量LLM |
| 2 | Task Planner | 5101 | ✅ | 意図から実行計画をステップバイステップで作成 |
| 3 | Task Critic | 5102 | ✅ | 実行結果を評価し、成功・失敗を判定 |
| 4 | RAG記憶進化 | 5103 | ✅ | 重要度スコア・重複チェック・時系列メモリ |

### ⚡ 優先度A：体感が一気に変わる機能（2/2完了）

| # | 機能 | ポート | 状態 | 説明 |
|---|------|--------|------|------|
| 5 | 汎用タスクキュー | 5104 | ✅ | Priority制御・Rate Limit管理 |
| 6 | UI操作機能 | 5105 | ✅ | 実行ボタン・モード切替・コストメーター |

### 🔧 統合・最適化（3/3完了）

| # | 機能 | ポート | 状態 | 説明 |
|---|------|--------|------|------|
| 7 | 統合オーケストレーター | 5106 | ✅ | Intent Router + Planner + Critic + Executor統合 |
| 8 | Executor拡張 | 5107 | ✅ | Task Plannerの実行計画に対応、実行結果をTask Criticに連携 |
| 9 | Portal統合 | 5108 | ✅ | UI操作機能をUnified Portal v2に統合 |

### 💰 優先度B：将来お金になるやつ（2/2完了）

| # | 機能 | ポート | 状態 | 説明 |
|---|------|--------|------|------|
| 10 | 成果物自動生成 | 5109 | ✅ | 日報→ブログ、構成ログ→note/Zenn記事、画像→テンプレ商品 |
| 11 | LLM最適化 | 5110 | ✅ | GPU効率化・フィルタ機能・動的モデル管理 |

### 🔍 追加機能

| # | 機能 | ポート | 状態 | 説明 |
|---|------|--------|------|------|
| 12 | サービス監視 | 5111 | ✅ | サービス停止の自動検知・再起動・メトリクス収集 |

---

## 🔧 各サービスの詳細

### 1. Intent Router (5100)

**役割**: ユーザー入力から意図を分類

**機能**:
- LLMベースの意図分類
- キーワードマッチング（フォールバック）
- バッチ分類対応

**利用可能な意図タイプ**:
- `conversation`: 会話・雑談
- `task_execution`: タスク実行
- `information_search`: 情報検索
- `image_generation`: 画像生成
- `code_generation`: コード生成
- `system_control`: システム制御
- `scheduling`: スケジューリング
- `data_analysis`: データ分析
- `unknown`: 不明

**設定ファイル**: `intent_router_config.json`

**API**:
- `POST /api/classify` - 意図分類
- `POST /api/classify/batch` - 一括分類
- `GET /api/config` - 設定取得
- `POST /api/config` - 設定更新

---

### 2. Task Planner (5101)

**役割**: 意図から実行計画をステップバイステップで作成

**機能**:
- LLMベースの計画生成
- 依存関係の管理
- 優先度の設定
- フォールバック計画

**実行計画の構造**:
```json
{
  "plan_id": "plan_20250128_123456",
  "intent_type": "image_generation",
  "steps": [
    {
      "step_id": "step_1",
      "description": "画像生成ワークフローを実行",
      "action": "execute_workflow",
      "target": "image_generation",
      "parameters": {},
      "dependencies": [],
      "estimated_duration": 60,
      "priority": "high"
    }
  ],
  "total_estimated_duration": 60,
  "priority": "high"
}
```

**設定ファイル**: `task_planner_config.json`

**API**:
- `POST /api/plan` - 実行計画作成
- `GET /api/config` - 設定取得
- `POST /api/config` - 設定更新

---

### 3. Task Critic (5102)

**役割**: 実行結果を評価し、成功・失敗を判定

**機能**:
- LLMベースの評価
- ルールベースの評価（フォールバック）
- 失敗理由の特定
- 改善提案の生成

**評価結果の構造**:
```json
{
  "evaluation": "success|partial_success|failure|uncertain",
  "score": 0.0-1.0,
  "failure_reason": "timeout|error|invalid_output|incomplete|quality_issue|unknown|null",
  "issues": ["問題点1", "問題点2"],
  "improvements": ["改善提案1", "改善提案2"],
  "confidence": 0.0-1.0,
  "reasoning": "評価理由"
}
```

**設定ファイル**: `task_critic_config.json`

**API**:
- `POST /api/evaluate` - 実行結果評価
- `GET /api/config` - 設定取得
- `POST /api/config` - 設定更新

---

### 4. RAG記憶進化 (5103)

**役割**: 重要度スコア・重複チェック・時系列メモリ

**機能**:
- 重要度スコア計算（LLMベース）
- 重複チェック（LLMベース）
- 時系列メモリ管理
- メモリ検索

**メモリエントリの構造**:
```json
{
  "id": "1",
  "content": "メモリ内容",
  "importance": 0.8,
  "timestamp": "2025-01-28T12:00:00",
  "metadata": {}
}
```

**設定ファイル**: `rag_memory_config.json`

**API**:
- `POST /api/add` - メモリ追加
- `POST /api/retrieve` - メモリ検索
- `GET /api/stats` - 統計情報

---

### 5. 汎用タスクキュー (5104)

**役割**: Priority制御・Rate Limit管理

**機能**:
- SQLiteベースのキュー管理
- 優先度制御（urgent/high/medium/low）
- Rate Limit管理
- リトライ機能
- ワーカーループ

**タスクの構造**:
```json
{
  "id": "task_123456",
  "task_type": "image_generation",
  "payload": {},
  "priority": 3,
  "status": "pending|running|completed|failed",
  "created_at": "2025-01-28T12:00:00",
  "scheduled_at": "2025-01-28T12:00:00",
  "retries": 0
}
```

**設定ファイル**: `task_queue_config.json`

**API**:
- `POST /api/enqueue` - タスクエンキュー
- `GET /api/task/<task_id>` - タスク状態取得
- `GET /api/status` - キュー状態取得
- `GET /api/config` - 設定取得
- `POST /api/config` - 設定更新

---

### 6. UI操作機能 (5105)

**役割**: 実行ボタン・モード切替・コストメーター

**機能**:
- タスク実行API
- モード切替（work/creative/fun/auto）
- コストメーター
- 実行履歴

**設定ファイル**: `ui_operations_config.json`

**API**:
- `POST /api/execute` - タスク実行
- `POST /api/mode` - モード設定
- `GET /api/mode` - モード取得
- `GET /api/cost` - コスト取得

---

### 7. 統合オーケストレーター (5106)

**役割**: Intent Router + Planner + Critic + Executor統合

**機能**:
- エンドツーエンドの実行フロー
- 各サービスとの連携
- 実行履歴管理
- 自動評価・記憶保存

**実行フロー**:
1. 意図分類
2. 実行計画作成
3. タスクエンキュー
4. タスク実行待機
5. 実行結果評価
6. 記憶保存

**設定ファイル**: `unified_orchestrator_config.json`

**API**:
- `POST /api/execute` - タスク実行（エンドツーエンド）
- `GET /api/history` - 実行履歴取得
- `GET /api/execution/<execution_id>` - 実行結果取得

---

### 8. Executor拡張 (5107)

**役割**: Task Plannerの実行計画に対応、実行結果をTask Criticに連携

**機能**:
- n8nワークフロー実行
- API呼び出し（GET/POST）
- スクリプト実行
- コマンド実行
- 依存関係の管理
- 実行結果の評価連携

**実行アクション**:
- `execute_workflow`: n8nワークフロー実行
- `call_api`: API呼び出し
- `run_script`: スクリプト実行
- `execute_command`: コマンド実行

**設定ファイル**: `task_executor_config.json`

**API**:
- `POST /api/execute` - 実行計画実行
- `POST /api/evaluate` - 実行結果評価

---

### 9. Portal統合 (5108)

**役割**: UI操作機能をUnified Portal v2に統合

**機能**:
- Unified Orchestrator経由のタスク実行
- モード切替
- コストメーター
- キュー状態表示
- 実行履歴表示

**UIコンポーネント**:
- `portal_ui_components.js` - JavaScriptコンポーネント
- `portal_ui_styles.css` - CSSスタイル

**API**:
- `POST /api/execute` - タスク実行
- `GET /api/mode` - モード取得
- `POST /api/mode` - モード設定
- `GET /api/cost` - コスト取得
- `GET /api/queue/status` - キュー状態取得
- `GET /api/history` - 実行履歴取得
- `GET /api/execution/<execution_id>` - 実行結果取得

---

### 10. 成果物自動生成 (5109)

**役割**: 日報→ブログ、構成ログ→note/Zenn記事、画像→テンプレ商品

**機能**:
- 日報からブログ草稿生成
- 構成ログからnote/Zenn記事生成
- 画像生成物をテンプレート商品として保存
- SQLiteベースのコンテンツ管理

**生成ルール**:
- `daily_report` → `blog_draft`
- `config_log` → `note_article`, `zenn_article`
- `image_generation` → `template_product`

**設定ファイル**: `content_generation_config.json`

**API**:
- `POST /api/generate/blog` - ブログ生成
- `POST /api/generate/article` - 記事生成
- `POST /api/create/template` - テンプレート作成
- `GET /api/contents` - 生成コンテンツ取得

---

### 11. LLM最適化 (5110)

**役割**: GPU効率化・フィルタ機能・動的モデル管理

**機能**:
- GPU状態監視
- モデル選択（役割別）
- フィルタ機能（超軽量モデル）
- 動的モデルロード/アンロード
- 最適化統計

**モデル役割**:
- `conversation`: 会話（軽量7B）
- `reasoning`: 判断（中型13B）
- `generation`: 生成（クラウド/重量）
- `filter`: フィルタ（超軽量）

**設定ファイル**: `llm_optimization_config.json`

**API**:
- `POST /api/filter` - リクエストフィルタ
- `POST /api/select-model` - モデル選択
- `GET /api/stats` - 最適化統計
- `POST /api/optimize` - 最適化実行

---

### 12. サービス監視 (5111)

**役割**: サービス停止の自動検知・再起動・メトリクス収集

**機能**:
- 定期的なヘルスチェック
- 自動再起動
- 再起動回数制限
- ステータスレポート

**設定ファイル**: `service_monitor_config.json`

**API**:
- `GET /api/status` - ステータス取得

---

## 🚀 インストール・セットアップ

### 前提条件

- Python 3.8以上
- Ollama（ローカルLLM）
- PowerShell 5.1以上（Windows）
- 管理者権限（自動起動設定時）

### 1. ディレクトリ移動

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
```

### 2. 依存パッケージのインストール

```powershell
pip install flask flask-cors httpx
```

### 3. 設定ファイルの確認

各サービスの設定ファイルを確認・編集：

- `intent_router_config.json`
- `task_planner_config.json`
- `task_critic_config.json`
- `rag_memory_config.json`
- `task_queue_config.json`
- `ui_operations_config.json`
- `unified_orchestrator_config.json`
- `task_executor_config.json`
- `content_generation_config.json`
- `llm_optimization_config.json`
- `service_monitor_config.json`

### 4. 全サービス起動

```powershell
.\start_all_services.ps1
```

### 5. 自動起動設定（初回のみ、管理者権限必要）

```powershell
# PowerShellを右クリック > 管理者として実行
.\setup_autostart.ps1
```

### 6. 監視システム起動（オプション）

```powershell
python service_monitor.py
```

---

## 📖 使用方法

### 基本的な使い方

#### 1. 状態確認

```powershell
.\check_all_services.ps1
```

#### 2. 全サービス起動

```powershell
.\start_all_services.ps1
```

#### 3. 全サービス停止

```powershell
.\stop_all_services.ps1
```

#### 4. テスト実行

```powershell
python test_all_services.py
```

### Unified Orchestrator経由での実行

```powershell
# タスク実行
$body = @{
    text = "画像を生成して"
    mode = "creative"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5106/api/execute" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

### Portal Integration経由での実行

```powershell
# タスク実行
$body = @{
    text = "画像を生成して"
    mode = "creative"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5108/api/execute" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

### 個別サービスAPI呼び出し

#### Intent Router

```powershell
$body = @{
    text = "画像を生成して"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5100/api/classify" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

#### Task Planner

```powershell
$body = @{
    text = "画像を生成して"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5101/api/plan" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

---

## 📡 API仕様

### 共通エンドポイント

すべてのサービスに共通：

- `GET /health` - ヘルスチェック

### Intent Router (5100)

#### `POST /api/classify`

意図を分類

**リクエスト**:
```json
{
  "text": "画像を生成して"
}
```

**レスポンス**:
```json
{
  "intent_type": "image_generation",
  "confidence": 0.9,
  "entities": {},
  "reasoning": "分類理由",
  "suggested_actions": ["execute_workflow"],
  "timestamp": "2025-01-28T12:00:00"
}
```

#### `POST /api/classify/batch`

一括分類

**リクエスト**:
```json
{
  "texts": ["画像を生成して", "メールを確認して"]
}
```

**レスポンス**:
```json
{
  "results": [
    {
      "intent_type": "image_generation",
      "confidence": 0.9,
      ...
    },
    {
      "intent_type": "information_search",
      "confidence": 0.8,
      ...
    }
  ]
}
```

### Task Planner (5101)

#### `POST /api/plan`

実行計画を作成

**リクエスト**:
```json
{
  "text": "画像を生成して"
}
```

**レスポンス**:
```json
{
  "plan_id": "plan_20250128_123456",
  "intent_type": "image_generation",
  "original_input": "画像を生成して",
  "steps": [
    {
      "step_id": "step_1",
      "description": "画像生成ワークフローを実行",
      "action": "execute_workflow",
      "target": "image_generation",
      "parameters": {},
      "dependencies": [],
      "estimated_duration": 60,
      "priority": "high"
    }
  ],
  "total_estimated_duration": 60,
  "priority": "high",
  "created_at": "2025-01-28T12:00:00"
}
```

### Task Critic (5102)

#### `POST /api/evaluate`

実行結果を評価

**リクエスト**:
```json
{
  "intent_type": "image_generation",
  "original_input": "画像を生成して",
  "plan": {
    "plan_id": "plan_20250128_123456",
    ...
  },
  "status": "completed",
  "output": {
    "result": "success"
  },
  "error": null,
  "duration": 45.5
}
```

**レスポンス**:
```json
{
  "evaluation": "success",
  "score": 0.9,
  "failure_reason": null,
  "issues": [],
  "improvements": [],
  "confidence": 0.95,
  "reasoning": "期待される出力が達成されました",
  "timestamp": "2025-01-28T12:00:00"
}
```

### RAG記憶進化 (5103)

#### `POST /api/add`

メモリを追加

**リクエスト**:
```json
{
  "content": "画像生成が成功した",
  "importance_score": 0.8,
  "metadata": {
    "intent_type": "image_generation"
  }
}
```

**レスポンス**:
```json
{
  "status": "success",
  "message": "メモリにコンテンツを追加しました",
  "entry": {
    "id": "1",
    "content": "画像生成が成功した",
    "importance": 0.8,
    "timestamp": "2025-01-28T12:00:00",
    "metadata": {}
  }
}
```

#### `POST /api/retrieve`

メモリを検索

**リクエスト**:
```json
{
  "query": "画像生成",
  "top_k": 5
}
```

**レスポンス**:
```json
{
  "status": "success",
  "query": "画像生成",
  "results": [
    {
      "id": "1",
      "content": "画像生成が成功した",
      "importance": 0.8,
      "timestamp": "2025-01-28T12:00:00",
      "metadata": {}
    }
  ]
}
```

### 汎用タスクキュー (5104)

#### `POST /api/enqueue`

タスクをエンキュー

**リクエスト**:
```json
{
  "task_type": "image_generation",
  "payload": {
    "input": "画像を生成して",
    "plan": {...}
  },
  "priority": "high"
}
```

**レスポンス**:
```json
{
  "status": "success",
  "task_id": "task_123456"
}
```

#### `GET /api/task/<task_id>`

タスク状態を取得

**レスポンス**:
```json
{
  "id": "task_123456",
  "status": "completed",
  "created_at": "2025-01-28T12:00:00",
  "last_attempt_at": "2025-01-28T12:01:00",
  "retries": 0,
  "error_message": null
}
```

#### `GET /api/status`

キュー状態を取得

**レスポンス**:
```json
{
  "status": "success",
  "queue_enabled": true,
  "total_tasks": 10,
  "pending_tasks": 2,
  "status_counts": {
    "pending": 2,
    "running": 1,
    "completed": 5,
    "failed": 2
  }
}
```

### UI操作機能 (5105)

#### `POST /api/execute`

タスク実行

**リクエスト**:
```json
{
  "input": "画像を生成して",
  "task_type": "image_generation",
  "priority": 1,
  "mode": "creative"
}
```

**レスポンス**:
```json
{
  "status": "success",
  "message": "タスクがキューに追加されました",
  "task_id": "task_123456",
  "intent": "image_generation",
  "execution_plan": [...]
}
```

#### `POST /api/mode`

モード設定

**リクエスト**:
```json
{
  "mode": "creative"
}
```

**レスポンス**:
```json
{
  "status": "success",
  "current_mode": "creative"
}
```

#### `GET /api/mode`

モード取得

**レスポンス**:
```json
{
  "current_mode": "creative"
}
```

#### `GET /api/cost`

コスト取得

**レスポンス**:
```json
{
  "status": "success",
  "today": "2025-01-28",
  "daily_cost": "123.45",
  "total_cost": "1234.56",
  "currency": "JPY"
}
```

### 統合オーケストレーター (5106)

#### `POST /api/execute`

タスク実行（エンドツーエンド）

**リクエスト**:
```json
{
  "text": "画像を生成して",
  "mode": "creative",
  "auto_evaluate": true,
  "save_to_memory": true
}
```

**レスポンス**:
```json
{
  "execution_id": "exec_20250128_123456",
  "input_text": "画像を生成して",
  "intent_type": "image_generation",
  "plan_id": "plan_20250128_123456",
  "task_id": "task_123456",
  "status": "completed",
  "result": {...},
  "evaluation": {...},
  "error": null,
  "created_at": "2025-01-28T12:00:00",
  "completed_at": "2025-01-28T12:01:00",
  "duration_seconds": 60.5
}
```

#### `GET /api/history`

実行履歴取得

**クエリパラメータ**:
- `limit`: 取得件数（デフォルト: 10）

**レスポンス**:
```json
{
  "results": [
    {
      "execution_id": "exec_20250128_123456",
      "input_text": "画像を生成して",
      "intent_type": "image_generation",
      "status": "completed",
      ...
    }
  ],
  "count": 10
}
```

#### `GET /api/execution/<execution_id>`

実行結果取得

**レスポンス**:
```json
{
  "execution_id": "exec_20250128_123456",
  "input_text": "画像を生成して",
  "intent_type": "image_generation",
  "status": "completed",
  "result": {...},
  "evaluation": {...},
  ...
}
```

### Executor拡張 (5107)

#### `POST /api/execute`

実行計画実行

**リクエスト**:
```json
{
  "plan": {
    "plan_id": "plan_20250128_123456",
    "steps": [...]
  },
  "execution_id": "exec_20250128_123456"
}
```

**レスポンス**:
```json
{
  "execution_id": "exec_20250128_123456",
  "plan_id": "plan_20250128_123456",
  "status": "completed",
  "steps": [...],
  "total_duration_seconds": 60.5,
  "result": {...},
  "error": null,
  "started_at": "2025-01-28T12:00:00",
  "completed_at": "2025-01-28T12:01:00"
}
```

#### `POST /api/evaluate`

実行結果評価

**リクエスト**:
```json
{
  "intent_type": "image_generation",
  "original_input": "画像を生成して",
  "plan": {...},
  "execution_result": {...}
}
```

**レスポンス**:
```json
{
  "evaluation": "success",
  "score": 0.9,
  ...
}
```

### Portal統合 (5108)

すべてのエンドポイントはUnified Orchestrator (5106)とUI操作機能 (5105)を経由します。

### 成果物自動生成 (5109)

#### `POST /api/generate/blog`

ブログ生成

**リクエスト**:
```json
{
  "daily_report": {
    "id": "report_123",
    "date": "2025-01-28",
    "content": "今日は..."
  }
}
```

**レスポンス**:
```json
{
  "content_id": "blog_20250128_123456",
  "source_type": "daily_report",
  "source_id": "report_123",
  "content_type": "blog_draft",
  "title": "タイトル",
  "content": "本文",
  "status": "draft",
  "created_at": "2025-01-28T12:00:00",
  ...
}
```

#### `POST /api/generate/article`

記事生成

**リクエスト**:
```json
{
  "config_log": {
    "id": "log_123",
    "title": "構成ログ",
    "content": "内容"
  }
}
```

**レスポンス**:
```json
{
  "results": [
    {
      "content_id": "note_20250128_123456",
      "content_type": "note_article",
      ...
    },
    {
      "content_id": "zenn_20250128_123456",
      "content_type": "zenn_article",
      ...
    }
  ],
  "count": 2
}
```

#### `POST /api/create/template`

テンプレート作成

**リクエスト**:
```json
{
  "image_info": {
    "id": "img_123",
    "path": "/path/to/image.png",
    "prompt": "プロンプト",
    "quality_score": 0.8
  }
}
```

**レスポンス**:
```json
{
  "content_id": "template_20250128_123456",
  "content_type": "template_product",
  ...
}
```

#### `GET /api/contents`

生成コンテンツ取得

**クエリパラメータ**:
- `content_type`: コンテンツタイプ（オプション）
- `status`: ステータス（オプション）
- `limit`: 取得件数（デフォルト: 20）

**レスポンス**:
```json
{
  "results": [...],
  "count": 10
}
```

### LLM最適化 (5110)

#### `POST /api/filter`

リクエストフィルタ

**リクエスト**:
```json
{
  "prompt": "画像を生成して"
}
```

**レスポンス**:
```json
{
  "should_process": true,
  "confidence": 0.9
}
```

#### `POST /api/select-model`

モデル選択

**リクエスト**:
```json
{
  "role": "conversation",
  "prompt": "こんにちは"
}
```

**レスポンス**:
```json
{
  "role": "conversation",
  "model": "llama3.2:3b"
}
```

#### `GET /api/stats`

最適化統計

**レスポンス**:
```json
{
  "total_models": 4,
  "loaded_models": 2,
  "gpu_status": {
    "utilization": 45.5,
    "vram_used_gb": 8.2,
    "vram_total_gb": 24.0,
    "available": true
  },
  "models": {...},
  "filter_enabled": true,
  "dynamic_loading_enabled": true
}
```

#### `POST /api/optimize`

最適化実行

**レスポンス**:
```json
{
  "status": "optimized"
}
```

### サービス監視 (5111)

#### `GET /api/status`

ステータス取得

**レスポンス**:
```json
{
  "timestamp": "2025-01-28T12:00:00",
  "total_services": 11,
  "running": 10,
  "stopped": 1,
  "error": 0,
  "services": {
    "Intent Router": {
      "name": "Intent Router",
      "port": 5100,
      "status": "running",
      "last_check": "2025-01-28T12:00:00",
      "restart_count": 0,
      "error_message": null
    },
    ...
  }
}
```

---

## ⚙️ 設定ファイル

### Intent Router (`intent_router_config.json`)

```json
{
  "ollama_url": "http://localhost:11434",
  "model": "llama3.2:3b",
  "use_llm": true,
  "intents": {
    "conversation": ["会話", "雑談"],
    "task_execution": ["実行", "作って"],
    "information_search": ["検索", "調べて"],
    "image_generation": ["画像", "生成"],
    "code_generation": ["コード", "実装"],
    "system_control": ["再起動", "停止"],
    "scheduling": ["予定", "カレンダー"],
    "data_analysis": ["分析", "統計"]
  }
}
```

### Task Planner (`task_planner_config.json`)

```json
{
  "ollama_url": "http://localhost:11434",
  "model": "llama3.2:3b",
  "intent_router_url": "http://localhost:5100",
  "max_steps": 10,
  "default_priority": "medium",
  "action_templates": {
    "image_generation": {
      "action": "execute_workflow",
      "target": "n8n_workflow",
      "workflow_name": "image_generation",
      "default_params": {}
    }
  }
}
```

### Task Critic (`task_critic_config.json`)

```json
{
  "ollama_url": "http://localhost:11434",
  "model": "llama3.2:3b",
  "success_threshold": 0.7,
  "partial_success_threshold": 0.4,
  "evaluation_criteria": {
    "success": {
      "score_range": [0.7, 1.0],
      "conditions": ["エラーがない", "期待される出力が得られた"]
    }
  }
}
```

### RAG記憶進化 (`rag_memory_config.json`)

```json
{
  "ollama_url": "http://localhost:11434",
  "model": "llama3.2:3b",
  "importance_threshold": 0.7,
  "duplicate_similarity_threshold": 0.9,
  "max_memory_entries": 1000
}
```

### 汎用タスクキュー (`task_queue_config.json`)

```json
{
  "queue_enabled": true,
  "worker_interval_seconds": 5,
  "max_retries": 3,
  "retry_delay_seconds": 60,
  "rate_limits": {
    "default": {
      "limit": 10,
      "window_seconds": 60
    },
    "high_priority": {
      "limit": 30,
      "window_seconds": 60
    }
  }
}
```

### UI操作機能 (`ui_operations_config.json`)

```json
{
  "current_mode": "stable",
  "api_costs": {},
  "service_urls": {
    "task_queue": "http://localhost:5104",
    "intent_router": "http://localhost:5100",
    "task_planner": "http://localhost:5101",
    "task_critic": "http://localhost:5102",
    "rag_memory": "http://localhost:5103"
  }
}
```

### 統合オーケストレーター (`unified_orchestrator_config.json`)

```json
{
  "auto_evaluate": true,
  "auto_retry": true,
  "max_retries": 3,
  "save_to_memory": true,
  "memory_importance_threshold": 0.6,
  "intent_router_url": "http://localhost:5100",
  "task_planner_url": "http://localhost:5101",
  "task_critic_url": "http://localhost:5102",
  "task_queue_url": "http://localhost:5104",
  "rag_memory_url": "http://localhost:5103"
}
```

### Executor拡張 (`task_executor_config.json`)

```json
{
  "n8n_url": "http://localhost:5678",
  "task_critic_url": "http://localhost:5102",
  "timeout_seconds": 300,
  "retry_on_failure": true,
  "max_retries": 3
}
```

### 成果物自動生成 (`content_generation_config.json`)

```json
{
  "ollama_url": "http://localhost:11434",
  "model": "qwen2.5:14b",
  "auto_generate": true,
  "generation_rules": {
    "daily_report": {
      "enabled": true,
      "target": "blog_draft",
      "template": "blog_template"
    },
    "config_log": {
      "enabled": true,
      "target": ["note_article", "zenn_article"],
      "template": "tech_article_template"
    },
    "image_generation": {
      "enabled": true,
      "target": "template_product",
      "min_quality_score": 0.7
    }
  }
}
```

### LLM最適化 (`llm_optimization_config.json`)

```json
{
  "ollama_url": "http://localhost:11434",
  "filter_model": "llama3.2:1b",
  "role_models": {
    "conversation": {
      "primary": "llama3.2:3b",
      "fallback": "qwen2.5:7b",
      "vram_gb": 4.0
    },
    "reasoning": {
      "primary": "qwen2.5:14b",
      "fallback": "llama3.1:8b",
      "vram_gb": 8.0
    },
    "generation": {
      "primary": "qwen2.5:32b",
      "fallback": "qwen2.5:14b",
      "vram_gb": 20.0
    },
    "filter": {
      "primary": "llama3.2:1b",
      "vram_gb": 2.0
    }
  },
  "gpu_efficiency": {
    "enable_dynamic_loading": true,
    "unload_idle_timeout_seconds": 300,
    "max_concurrent_models": 2,
    "vram_threshold_percent": 80
  },
  "filter": {
    "enabled": true,
    "threshold": 0.5
  }
}
```

### サービス監視 (`service_monitor_config.json`)

```json
{
  "services": [
    {"name": "Intent Router", "port": 5100, "script": "intent_router.py"},
    {"name": "Task Planner", "port": 5101, "script": "task_planner.py"},
    {"name": "Task Critic", "port": 5102, "script": "task_critic.py"},
    {"name": "RAG Memory", "port": 5103, "script": "rag_memory_enhanced.py"},
    {"name": "Task Queue", "port": 5104, "script": "task_queue_system.py"},
    {"name": "UI Operations", "port": 5105, "script": "ui_operations_api.py"},
    {"name": "Unified Orchestrator", "port": 5106, "script": "unified_orchestrator.py"},
    {"name": "Executor Enhanced", "port": 5107, "script": "task_executor_enhanced.py"},
    {"name": "Portal Integration", "port": 5108, "script": "portal_integration_api.py"},
    {"name": "Content Generation", "port": 5109, "script": "content_generation_loop.py"},
    {"name": "LLM Optimization", "port": 5110, "script": "llm_optimization.py"}
  ],
  "check_interval": 30,
  "max_restarts": 5,
  "restart_delay": 5
}
```

---

## 🔧 トラブルシューティング

### 問題1: サービスが起動しない

**症状**: ポートが開いていない、または応答がない

**解決方法**:
1. ログを確認
   ```powershell
   Get-ChildItem logs\*.log | Select-Object -Last 5
   ```

2. プロセスを確認
   ```powershell
   Get-Process python* | Where-Object {$_.Path -like "*manaos_integrations*"}
   ```

3. 手動で起動してエラーを確認
   ```powershell
   python intent_router.py
   ```

4. ポートが使用中か確認
   ```powershell
   netstat -ano | findstr "5100"
   ```

### 問題2: Ollama接続エラー

**症状**: LLMベースの機能が動作しない

**解決方法**:
1. Ollamaが起動しているか確認
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing
   ```

2. モデルがインストールされているか確認
   ```powershell
   ollama list
   ```

3. 必要なモデルをインストール
   ```powershell
   ollama pull llama3.2:3b
   ```

### 問題3: タイムアウトエラー

**症状**: Task PlannerやTask Criticがタイムアウトする

**解決方法**:
1. 軽量モデルを使用（設定ファイルで変更）
   ```json
   {
     "model": "llama3.2:3b"
   }
   ```

2. タイムアウト時間を延長（コード内で変更）
3. フォールバック機能が動作することを確認

### 問題4: 自動起動が動作しない

**症状**: システム再起動後、サービスが起動しない

**解決方法**:
1. タスクが登録されているか確認
   ```powershell
   Get-ScheduledTask -TaskName "ManaOS_StartAllServices"
   ```

2. タスクの状態を確認
   ```powershell
   Get-ScheduledTask -TaskName "ManaOS_StartAllServices" | Get-ScheduledTaskInfo
   ```

3. タスクを再登録
   ```powershell
   .\setup_autostart.ps1
   ```

### 問題5: エンコーディングエラー

**症状**: PowerShellスクリプトで文字化けやエラー

**解決方法**:
1. UTF-8（BOMなし）で保存されているか確認
2. PowerShellのエンコーディング設定を確認
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```

### 問題6: データベースエラー

**症状**: SQLiteデータベース関連のエラー

**解決方法**:
1. データベースファイルの権限を確認
2. データベースファイルを削除して再作成
   ```powershell
   Remove-Item task_queue.db -ErrorAction SilentlyContinue
   Remove-Item content_generation.db -ErrorAction SilentlyContinue
   ```

---

## 🚀 今後の拡張ポイント

### 優先度：高

1. **エラー通知機能**
   - メール通知
   - Slack通知
   - テレグラム通知

2. **メトリクス収集・可視化**
   - Prometheus統合
   - Grafanaダッシュボード
   - カスタムダッシュボード

3. **設定管理の改善**
   - 環境変数対応
   - 設定ファイルの検証
   - 設定の動的更新

### 優先度：中

4. **パフォーマンス最適化**
   - キャッシュ機能
   - 非同期処理の強化
   - リソース使用量の最適化

5. **セキュリティ強化**
   - 認証・認可
   - APIキー管理
   - レート制限の強化

6. **systemd統合**
   - Linux環境での自動起動
   - systemdサービスファイル

7. **Windowsサービス化**
   - Windowsサービスとしての登録
   - サービス管理UI

### 優先度：低

8. **ドキュメント整備**
   - API仕様書（OpenAPI）
   - 運用マニュアル
   - トラブルシューティングガイド

9. **テストの拡充**
   - 統合テスト
   - 負荷テスト
   - E2Eテスト

10. **多言語対応**
    - 英語対応
    - その他の言語対応

---

## 📊 パフォーマンス指標

### 現在の性能

- **意図分類**: 平均2-5秒（LLM使用時）
- **計画作成**: 平均10-30秒（LLM使用時）
- **結果評価**: 平均5-15秒（LLM使用時）
- **タスク実行**: タスク依存（n8nワークフロー: 10-60秒）

### 最適化の余地

- **キャッシュ**: 同じリクエストをキャッシュして応答速度向上
- **非同期処理**: 重い処理を非同期で実行
- **モデル最適化**: より軽量なモデルの使用

---

## 🔐 セキュリティ考慮事項

### 現在の実装

- **認証**: なし（ローカル環境想定）
- **認可**: なし（ローカル環境想定）
- **暗号化**: なし（ローカル環境想定）

### 本番環境での推奨事項

1. **認証・認可の実装**
   - APIキー認証
   - JWT認証
   - OAuth2統合

2. **HTTPSの使用**
   - リバースプロキシ（nginx等）
   - SSL/TLS証明書

3. **レート制限の強化**
   - IPベースのレート制限
   - ユーザーベースのレート制限

4. **ログの保護**
   - 機密情報のマスキング
   - ログの暗号化

---

## 📝 ログ管理

### ログファイルの場所

```
manaos_integrations/logs/
├── intent_router.log
├── intent_router_error.log
├── task_planner.log
├── task_planner_error.log
├── ...
```

### ログローテーション

- 最大ファイルサイズ: 10MB
- バックアップファイル数: 5
- 自動ローテーション: 有効

### ログレベル

- `INFO`: 通常の動作ログ
- `WARNING`: 警告ログ
- `ERROR`: エラーログ

---

## 🎯 使用例

### 例1: 画像生成タスクの実行

```powershell
# Unified Orchestrator経由で実行
$body = @{
    text = "猫の画像を生成して"
    mode = "creative"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:5106/api/execute" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

$result = $response.Content | ConvertFrom-Json
Write-Host "実行ID: $($result.execution_id)"
Write-Host "ステータス: $($result.status)"
```

### 例2: 実行履歴の確認

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:5106/api/history?limit=5" `
    -UseBasicParsing

$history = $response.Content | ConvertFrom-Json
$history.results | Format-Table execution_id, input_text, status, duration_seconds
```

### 例3: モード切替

```powershell
$body = @{
    mode = "work"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5105/api/mode" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

### 例4: コスト確認

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:5105/api/cost" `
    -UseBasicParsing

$cost = $response.Content | ConvertFrom-Json
Write-Host "今日のコスト: ¥$($cost.daily_cost)"
Write-Host "合計コスト: ¥$($cost.total_cost)"
```

---

## 📚 関連ドキュメント

- `QUICK_START.md` - クイックスタートガイド
- `COMPLETE_SETUP.md` - セットアップ完了レポート
- `INTEGRATION_STATUS.md` - 統合状況レポート
- `FINAL_STATUS.md` - 最終状態レポート
- `ISSUES_RESOLVED.md` - 問題解決レポート
- `TEST_RESULTS.md` - テスト結果レポート

---

## ✅ まとめ

ManaOSは完全に実装され、動作確認済みです。

- ✅ **全11サービス実装完了**
- ✅ **動作確認完了（11/11）**
- ✅ **自動起動設定完了**
- ✅ **監視システム実装完了**
- ✅ **統一ログ管理実装完了**
- ✅ **実際に動作する実装（言葉のみではない）**

**ManaOSは「もう一人のマナ」として完全に動作可能な状態です！** 🎉

---

**最終更新**: 2025-01-28  
**バージョン**: 1.0.0  
**状態**: 完全実装・動作確認済み・自動起動設定済み

