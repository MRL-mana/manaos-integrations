# 🚀 OH MY OPENCODE 基本統合ドキュメント

**作成日**: 2025-01-28  
**フェーズ**: Phase 1 - 基本統合  
**状態**: ✅ 実装完了

---

## 📋 概要

OH MY OPENCODEとManaOSの基本統合を実装しました。これにより、ManaOSからOH MY OPENCODEを呼び出してコーディングタスクを実行できるようになります。

---

## ✅ 実装完了項目

### 1. OH MY OPENCODE API統合 ✅

**ファイル**: `oh_my_opencode_integration.py`

**機能**:
- APIクライアントの実装（httpx使用）
- 認証・設定管理
- エラーハンドリング（ManaOS統一エラーハンドラー統合）
- 非同期実行サポート

**主要クラス**:
- `OHMyOpenCodeIntegration`: メイン統合クラス
- `OHMyOpenCodeTask`: タスクデータクラス
- `OHMyOpenCodeResult`: 実行結果データクラス
- `ExecutionMode`: 実行モードEnum（NORMAL/ULTRA_WORK）
- `TaskType`: タスクタイプEnum

### 2. 設定ファイル ✅

**ファイル**: `oh_my_opencode_config.yaml`

**設定項目**:
- API設定（base_url, api_key, timeout）
- 実行モード設定（default_mode, max_iterations, max_execution_time）
- Ultra Workモード設定（enabled, allowed_task_types, require_approval）
- コスト管理設定（daily_limit, monthly_limit, warning_threshold）
- Kill Switch設定（max_execution_time, max_iterations, detect_infinite_loop）
- Trinity統合設定（remi_integration, luna_integration, mina_integration）
- LLMルーティング統合設定（use_manaos_routing, fallback_to_local）

### 3. ManaOS LLMルーティング統合 ✅

**実装内容**:
- ManaOS LLMルーティングシステムとの統合
- タスクタイプに応じた自動モデル選択
- ローカルモデルへのフォールバック機能

**タスクタイプマッピング**:
- `specification` → `reasoning`（推論モデル）
- `complex_bug` → `reasoning`（推論モデル）
- `architecture_design` → `reasoning`（推論モデル）
- `code_generation` → `automation`（自動処理モデル）
- `code_review` → `reasoning`（推論モデル）
- `refactoring` → `automation`（自動処理モデル）
- `general` → `automation`（自動処理モデル）

### 4. 基本実行フロー ✅

**実装内容**:
- 通常モードの実行
- 結果の取得・保存
- 実行履歴の管理

**実行フロー**:
```
1. タスク作成
2. コストチェック
3. Ultra Workモード制限チェック（該当時）
4. Trinity統合コンテキスト準備（オプション）
5. モデル選択（LLMルーティング統合）
6. OH MY OPENCODE API呼び出し
7. 結果取得・保存
8. コスト記録
```

### 5. コスト管理統合（基本） ✅

**ファイル**: `oh_my_opencode_cost_manager.py`

**機能**:
- 日次・月次コスト上限管理
- コスト履歴の記録・保存
- 警告閾値チェック
- 自動停止機能

**主要クラス**:
- `OHMyOpenCodeCostManager`: コスト管理クラス
- `CostRecord`: コスト記録データクラス

---

## 🚀 使用方法

### 基本的な使い方

```python
from oh_my_opencode_integration import (
    OHMyOpenCodeIntegration,
    ExecutionMode,
    TaskType
)
import asyncio

async def main():
    # 統合クラスの初期化
    integration = OHMyOpenCodeIntegration()
    
    if not integration.initialize():
        print("初期化に失敗しました")
        return
    
    # タスク実行
    result = await integration.execute_task(
        task_description="PythonでREST APIを作成してください",
        mode=ExecutionMode.NORMAL,
        task_type=TaskType.CODE_GENERATION
    )
    
    print(f"実行結果: {result.status}")
    print(f"コスト: ${result.cost:.2f}")
    print(f"実行時間: {result.execution_time:.2f}秒")
    
    if result.status == "success":
        print(f"結果: {result.result}")

asyncio.run(main())
```

### 環境変数の設定

```bash
# .envファイルまたは環境変数に設定
export OH_MY_OPENCODE_API_KEY="your_api_key_here"
```

### 設定ファイルのカスタマイズ

`oh_my_opencode_config.yaml`を編集して設定をカスタマイズできます。

```yaml
# 例: 日次コスト上限を変更
cost_management:
  daily_limit: 200.0  # $100 → $200に変更
```

---

## 🔧 APIリファレンス

### `OHMyOpenCodeIntegration`

#### `execute_task()`

タスクを実行します。

**パラメータ**:
- `task_description` (str): タスクの説明
- `mode` (ExecutionMode, optional): 実行モード（NORMAL/ULTRA_WORK）
- `task_type` (TaskType, optional): タスクタイプ
- `use_trinity` (bool, optional): Trinity統合を使用するか

**戻り値**:
- `OHMyOpenCodeResult`: 実行結果

**例外**:
- `CostLimitExceededError`: コスト上限超過
- `UltraWorkNotAllowedError`: Ultra Workモード使用不可

#### `kill_task()`

タスクを強制停止します（Kill Switch）。

**パラメータ**:
- `task_id` (str): タスクID

**戻り値**:
- `bool`: 停止成功かどうか

#### `get_status()`

状態を取得します。

**戻り値**:
- `Dict[str, Any]`: 状態情報

---

## 📊 コスト管理

### コスト統計の取得

```python
from oh_my_opencode_cost_manager import OHMyOpenCodeCostManager

cost_manager = OHMyOpenCodeCostManager()
stats = cost_manager.get_statistics()

print(f"日次コスト: ${stats['daily_cost']:.2f} / ${stats['daily_limit']:.2f}")
print(f"月次コスト: ${stats['monthly_cost']:.2f} / ${stats['monthly_limit']:.2f}")
print(f"タスク数: {stats['total_tasks']}")
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

## 📝 次のステップ

Phase 1の基本統合が完了しました。次のフェーズでは以下を実装予定です：

- **Phase 2**: Trinity統合（Remi/Luna/Mina統合）
- **Phase 3**: コスト管理・暴走防止の強化
- **Phase 4**: 高度な最適化

---

## 📚 参考資料

- [OH MY OPENCODE統合計画書](./OH_MY_OPENCODE_INTEGRATION_PLAN.md)
- [ManaOS LLMルーティング](./README_LLM_ROUTING.md)
- [ManaOSコスト管理](./ui_operations_config.json)

---

**作成者**: ManaOS Integration Team  
**最終更新**: 2025-01-28
