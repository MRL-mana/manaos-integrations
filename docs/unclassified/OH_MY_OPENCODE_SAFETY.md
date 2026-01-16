# 🚨 OH MY OPENCODE 安全性ドキュメント

**作成日**: 2025-01-28  
**フェーズ**: Phase 3 - コスト管理・暴走防止  
**状態**: ✅ 実装完了

---

## 📋 概要

OH MY OPENCODEは強力なツールですが、適切な制御なしでは暴走や高コストのリスクがあります。このドキュメントでは、安全性を確保するための機能と使用方法を説明します。

---

## 🛑 Kill Switch（緊急停止）

### 機能

Kill Switchは、タスクの実行を強制停止する機能です。

**停止理由**:
- **手動停止**: ユーザーが明示的に停止
- **実行時間制限**: 最大実行時間を超過
- **反復回数制限**: 最大反復回数を超過
- **無限ループ検知**: 同じエラーが繰り返される
- **コスト上限**: コスト上限を超過
- **エラー閾値**: エラーが一定回数発生

### 使用方法

```python
from oh_my_opencode_integration import OHMyOpenCodeIntegration

integration = OHMyOpenCodeIntegration()

# タスク実行中に停止
integration.kill_task(task_id="task_12345")
```

### 設定

`oh_my_opencode_config.yaml`で設定できます：

```yaml
# Kill Switch設定
kill_switch:
  enabled: true
  max_execution_time: 3600  # 最大実行時間（秒）
  max_iterations: 20  # 最大反復回数
  detect_infinite_loop: true  # 無限ループ検知
  auto_kill_on_error: false  # エラー時の自動停止（デフォルト: false）
```

### 無限ループ検知

同じエラーが3回以上繰り返される場合、無限ループとして検知されます：

```python
# エラーパターンの履歴を追跡
# 直近3回のエラーが同じ場合 → 無限ループ検知
# 直近5回のエラーが2種類以下の場合 → 無限ループ検知
```

---

## 💰 コスト管理

### 機能

コスト管理は、OH MY OPENCODEの使用コストを監視・制限する機能です。

**管理項目**:
- **タスクあたりのコスト上限**: 各タスクの最大コスト
- **日次コスト上限**: 1日の最大コスト
- **月次コスト上限**: 1ヶ月の最大コスト
- **警告閾値**: コストが上限の80%に達した場合に警告

### 使用方法

```python
from oh_my_opencode_cost_manager import OHMyOpenCodeCostManager

cost_manager = OHMyOpenCodeCostManager(
    daily_limit=100.0,
    monthly_limit=2000.0,
    warning_threshold=0.8
)

# コスト上限チェック
can_execute, warning = cost_manager.check_limit(estimated_cost=10.0)

if not can_execute:
    print(f"実行不可: {warning}")
elif warning:
    print(f"警告: {warning}")

# コスト記録
cost_manager.record_cost(
    task_id="task_12345",
    cost=5.0,
    task_type="code_generation",
    mode="normal"
)

# 統計情報取得
stats = cost_manager.get_statistics()
print(f"日次コスト: ${stats['daily_cost']:.2f} / ${stats['daily_limit']:.2f}")
print(f"月次コスト: ${stats['monthly_cost']:.2f} / ${stats['monthly_limit']:.2f}")
```

### 設定

`oh_my_opencode_config.yaml`で設定できます：

```yaml
# コスト管理
cost_management:
  enabled: true
  daily_limit: 100.0  # 日次コスト上限
  monthly_limit: 2000.0  # 月次コスト上限
  warning_threshold: 0.8  # 警告閾値（80%）
  auto_stop: true  # 上限到達時に自動停止
```

### コスト上限の推奨値

| モード | タスクあたり上限 | 日次上限 | 月次上限 |
|--------|----------------|---------|---------|
| **通常モード** | $10 | $100 | $2000 |
| **Ultra Workモード** | $100 | $500 | $10000 |

---

## ⚠️ Ultra Workモード制限

### 機能

Ultra Workモードは高コストになる可能性があるため、厳格な制限が設けられています。

**制限事項**:
- **許可されたタスクタイプのみ**: 仕様策定・難解バグ・初期アーキ設計
- **承認プロセス**: 承認が必要な場合、自動的に承認をリクエスト
- **自動無効化**: コスト上限到達時に自動無効化

### 許可されたタスクタイプ

- `specification`（仕様策定）
- `complex_bug`（難解バグ）
- `architecture_design`（初期アーキ設計）

### 承認プロセス

承認が必要な場合、以下のプロセスが実行されます：

1. **承認リクエスト**: タスクタイプと推定コストを記録
2. **通知**: Slack通知（将来実装予定）
3. **承認待ち**: 承認が得られるまで実行を停止
4. **実行**: 承認後に実行

### 設定

`oh_my_opencode_config.yaml`で設定できます：

```yaml
# Ultra Workモード設定
ultra_work:
  enabled: false  # デフォルト無効
  allowed_task_types:
    - "specification"  # 仕様策定
    - "complex_bug"  # 難解バグ
    - "architecture_design"  # 初期アーキ設計
  require_approval: true  # 承認が必要
  cost_limit_per_task: 100.0  # タスクあたりのコスト上限
```

---

## 🔒 安全性のベストプラクティス

### 1. Kill Switchを有効にする

```yaml
kill_switch:
  enabled: true
  max_execution_time: 3600  # 1時間
  max_iterations: 20
  detect_infinite_loop: true
```

### 2. コスト上限を設定する

```yaml
cost_management:
  enabled: true
  daily_limit: 100.0
  monthly_limit: 2000.0
  auto_stop: true
```

### 3. Ultra Workモードを制限する

```yaml
ultra_work:
  enabled: false  # デフォルト無効
  require_approval: true  # 承認が必要
```

### 4. 定期的にコストを確認する

```python
from oh_my_opencode_cost_manager import OHMyOpenCodeCostManager

cost_manager = OHMyOpenCodeCostManager()
stats = cost_manager.get_statistics()

if stats['daily_usage_percent'] > 80:
    print("警告: 日次コストが80%を超えています")
```

### 5. 実行時間を監視する

```python
# Kill Switchで実行時間を監視
kill_switch = OHMyOpenCodeKillSwitch(max_execution_time=3600)

# タスク登録
monitor = kill_switch.register_task(task_id)

# 定期的にチェック
can_continue = kill_switch.update_task(task_id, iteration=current_iteration)
```

---

## 🚨 緊急時の対応

### タスクが暴走している場合

1. **Kill Switchで停止**:
   ```python
   integration.kill_task(task_id)
   ```

2. **コスト上限を確認**:
   ```python
   stats = cost_manager.get_statistics()
   print(f"日次コスト: ${stats['daily_cost']:.2f}")
   ```

3. **設定を確認**:
   - Kill Switchが有効か
   - コスト上限が適切か
   - Ultra Workモードが無効か

### コストが予想以上に高い場合

1. **コスト履歴を確認**:
   ```python
   stats = cost_manager.get_statistics()
   print(f"タスクタイプ別コスト: {stats['task_type_costs']}")
   print(f"モード別コスト: {stats['mode_costs']}")
   ```

2. **コスト上限を下げる**:
   ```yaml
   cost_management:
     daily_limit: 50.0  # 100.0 → 50.0に下げる
   ```

3. **Ultra Workモードを無効にする**:
   ```yaml
   ultra_work:
     enabled: false
   ```

---

## 📊 監視とアラート

### 監視項目

- **実行時間**: 各タスクの実行時間
- **コスト**: 各タスクのコスト
- **反復回数**: Ralph Wiggum Loopの反復回数
- **エラー数**: 発生したエラーの数
- **成功率**: タスクの成功率

### アラート条件

- **コスト警告**: 日次・月次コストが80%に達した場合
- **実行時間警告**: 実行時間が上限の80%に達した場合
- **エラー警告**: エラーが一定回数発生した場合
- **無限ループ警告**: 無限ループが検知された場合

---

## 📚 参考資料

- [OH MY OPENCODE統合計画書](./OH_MY_OPENCODE_INTEGRATION_PLAN.md)
- [OH MY OPENCODE基本統合ドキュメント](./OH_MY_OPENCODE_BASIC_INTEGRATION.md)
- [OH MY OPENCODE Trinity統合ドキュメント](./OH_MY_OPENCODE_TRINITY_INTEGRATION.md)

---

## 💬 まとめ

**安全性の3つの柱**:

1. **Kill Switch**: 緊急停止・実行時間制限・無限ループ検知
2. **コスト管理**: タスクあたり上限・日次・月次上限・警告
3. **Ultra Work制限**: 許可されたタスクタイプのみ・承認プロセス・自動無効化

**「最強」ではなく「最も制御が難しいが、制御できたら最強」**

適切な制御機能を使用することで、OH MY OPENCODEを安全に運用できます。

---

**作成者**: ManaOS Integration Team  
**最終更新**: 2025-01-28
