# 🚀 OH MY OPENCODE × ManaOS 統合

**状態**: Phase 1 完了 ✅  
**最終更新**: 2025-01-28

---

## 📋 概要

OH MY OPENCODEは「次世代コーディングエージェントの完成形にかなり近い」ツールです。ManaOSとの統合により、以下の機能を提供します：

- **マルチエージェント実行**: Trinity Systemとの統合
- **コスト最適化**: ManaOS LLMルーティングによるモデル選択最適化
- **暴走防止**: Kill Switchとコスト上限による安全な運用
- **Ultra Workモード**: ピンポイント運用で最大効果

---

## 🚀 クイックスタート

### 1. 環境変数の設定

```bash
# .envファイルまたは環境変数に設定
export OH_MY_OPENCODE_API_KEY="your_api_key_here"
```

### 2. インストール

```bash
# 必要なパッケージのインストール
pip install httpx pyyaml python-dotenv
```

### 3. 基本的な使い方

```python
from oh_my_opencode_integration import (
    OHMyOpenCodeIntegration,
    ExecutionMode,
    TaskType
)
import asyncio

async def main():
    integration = OHMyOpenCodeIntegration()
    
    if not integration.initialize():
        print("初期化に失敗しました")
        return
    
    result = await integration.execute_task(
        task_description="PythonでREST APIを作成してください",
        mode=ExecutionMode.NORMAL,
        task_type=TaskType.CODE_GENERATION
    )
    
    print(f"実行結果: {result.status}")
    print(f"コスト: ${result.cost:.2f}")

asyncio.run(main())
```

### 4. テスト実行

```bash
python test_oh_my_opencode.py
```

---

## 📁 ファイル構成

```
manaos_integrations/
├── oh_my_opencode_integration.py      # メイン統合クラス
├── oh_my_opencode_cost_manager.py     # コスト管理モジュール
├── oh_my_opencode_config.yaml         # 設定ファイル
├── test_oh_my_opencode.py             # テストスクリプト
├── OH_MY_OPENCODE_INTEGRATION_PLAN.md # 統合計画書
├── OH_MY_OPENCODE_BASIC_INTEGRATION.md # 基本統合ドキュメント
└── README_OH_MY_OPENCODE.md           # このファイル
```

---

## ⚙️ 設定

### 設定ファイル: `oh_my_opencode_config.yaml`

主要な設定項目：

- **API設定**: base_url, api_key, timeout
- **実行モード**: default_mode, max_iterations, max_execution_time
- **Ultra Workモード**: enabled, allowed_task_types, require_approval
- **コスト管理**: daily_limit, monthly_limit, warning_threshold
- **Kill Switch**: max_execution_time, max_iterations, detect_infinite_loop
- **Trinity統合**: remi_integration, luna_integration, mina_integration
- **LLMルーティング**: use_manaos_routing, fallback_to_local

詳細は `oh_my_opencode_config.yaml` を参照してください。

---

## 🎯 実行モード

### Normal Mode（通常モード）

コスト最適化を重視したモード。一般的なタスクに使用します。

```python
result = await integration.execute_task(
    task_description="コードをリファクタリングしてください",
    mode=ExecutionMode.NORMAL,
    task_type=TaskType.REFACTORING
)
```

### Ultra Work Mode（Ultra Workモード）

品質優先のモード。以下のタスクタイプのみ使用可能：

- `specification`（仕様策定）
- `complex_bug`（難解バグ）
- `architecture_design`（初期アーキ設計）

```python
result = await integration.execute_task(
    task_description="システムアーキテクチャを設計してください",
    mode=ExecutionMode.ULTRA_WORK,
    task_type=TaskType.ARCHITECTURE_DESIGN
)
```

---

## 💰 コスト管理

### コスト統計の取得

```python
from oh_my_opencode_cost_manager import OHMyOpenCodeCostManager

cost_manager = OHMyOpenCodeCostManager()
stats = cost_manager.get_statistics()

print(f"日次コスト: ${stats['daily_cost']:.2f} / ${stats['daily_limit']:.2f}")
print(f"月次コスト: ${stats['monthly_cost']:.2f} / ${stats['monthly_limit']:.2f}")
```

### コスト上限チェック

```python
can_execute, warning = cost_manager.check_limit(estimated_cost=10.0)

if not can_execute:
    print(f"実行不可: {warning}")
elif warning:
    print(f"警告: {warning}")
```

---

## 🚨 エラーハンドリング

### コスト上限超過

```python
from oh_my_opencode_integration import CostLimitExceededError

try:
    result = await integration.execute_task("タスク説明")
except CostLimitExceededError as e:
    print(f"コスト上限超過: {e}")
```

### Ultra Workモード使用不可

```python
from oh_my_opencode_integration import UltraWorkNotAllowedError

try:
    result = await integration.execute_task(
        "タスク説明",
        mode=ExecutionMode.ULTRA_WORK,
        task_type=TaskType.GENERAL  # 許可されていないタスクタイプ
    )
except UltraWorkNotAllowedError as e:
    print(f"Ultra Workモード使用不可: {e}")
```

---

## 🔧 Kill Switch

タスクを強制停止できます。

```python
# タスク実行中に停止
integration.kill_task(task_id="task_12345")
```

---

## 📊 統合アーキテクチャ

```
[ユーザー要求]
  ↓
[ManaOS Intent Router] - 意図分類
  ↓
[OH MY OPENCODE統合レイヤー]
  ├─ [Sisyphus] - 統制役（Remi統合）
  ├─ [Ralph Wiggum Loop] - 失敗検知（Luna統合）
  └─ [学習システム] - 記憶（Mina統合）
  ↓
[ManaOS LLMルーティング] - モデル選択最適化
  ↓
[OH MY OPENCODE実行]
  ├─ 通常モード（コスト最適化）
  └─ Ultra Workモード（品質優先・制限付き）
  ↓
[ManaOSコスト管理] - 監視・制限
  ↓
[ManaOS Kill Switch] - 緊急停止（必要時）
  ↓
[結果保存] - Obsidian / Notion
```

---

## 📚 ドキュメント

- [統合計画書](./OH_MY_OPENCODE_INTEGRATION_PLAN.md) - 全体計画
- [基本統合ドキュメント](./OH_MY_OPENCODE_BASIC_INTEGRATION.md) - Phase 1詳細
- [ManaOS LLMルーティング](./README_LLM_ROUTING.md) - LLMルーティング詳細

---

## 🎯 次のステップ

Phase 1の基本統合が完了しました。次のフェーズでは以下を実装予定です：

- **Phase 2**: Trinity統合（Remi/Luna/Mina統合）
- **Phase 3**: コスト管理・暴走防止の強化
- **Phase 4**: 高度な最適化

---

## ⚠️ 注意事項

1. **コスト管理**: Ultra Workモードは高コストになる可能性があります。使用前にコスト上限を確認してください。

2. **APIキー**: OH MY OPENCODE APIキーが必要です。環境変数に設定してください。

3. **暴走防止**: Kill Switchとコスト上限を有効にして、安全に運用してください。

4. **Ultra Workモード**: 仕様策定・難解バグ・初期アーキ設計のみ使用可能です。

---

## 💬 まとめ

**OH MY OPENCODE × ManaOS = 思想的に相性100%**

- **Trinity思想**: 役割分担で最適化
- **コスト最適化**: LLMルーティングで最適化
- **暴走防止**: Kill Switchで安全に運用
- **Ultra Workモード**: ピンポイント運用で最大効果

**「最強」ではなく「最も制御が難しいが、制御できたら最強」**

ManaOSの制御機能で、OH MY OPENCODEを安全に運用できます。

---

**作成者**: ManaOS Integration Team  
**最終更新**: 2025-01-28
