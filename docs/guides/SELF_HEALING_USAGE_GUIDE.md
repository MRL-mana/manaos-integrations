# 🔧 ManaOS 自己修復機能 使用ガイド

**更新日**: 2026-01-04  
**完成度**: 約73%（大幅向上！）

---

## 📋 概要

ManaOSの包括的自己修復システムは、エラーの自動検知・学習・修復を行う高度なシステムです。以下の機能を提供します：

- ✅ エラーパターンの自動学習
- ✅ 修復アクションの自動選択
- ✅ 修復履歴の追跡
- ✅ 修復成功率の分析
- ✅ データベース/ストレージの自動修復
- ✅ ネットワーク接続の自動修復
- ✅ 設定ファイルの自動修復
- ✅ リソース不足時の自動修復

---

## 🚀 基本的な使い方

### 1. 自己修復システムの初期化

```python
from comprehensive_self_capabilities_system import ComprehensiveSelfCapabilitiesSystem

# システムを初期化
self_healing = ComprehensiveSelfCapabilitiesSystem()
```

### 2. エラーの自動修復

```python
try:
    # 何らかの処理
    result = some_operation()
except Exception as e:
    # 自動修復を実行
    repair_result = self_healing.auto_repair(
        error=e,
        context={
            "operation": "some_operation",
            "service_name": "my_service"
        }
    )
    
    if repair_result.get("success"):
        print(f"✅ 修復成功: {repair_result.get('message')}")
    else:
        print(f"❌ 修復失敗: {repair_result.get('error')}")
```

### 3. エラーパターンの学習

```python
try:
    # 処理
    pass
except Exception as e:
    # エラーパターンを学習
    self_healing.learn_error_pattern(
        error=e,
        context={"operation": "my_operation"}
    )
```

---

## 🔧 修復アクションの種類

### 1. サービス再起動 (`restart_service`)

```python
repair_result = self_healing.auto_repair(
    error=ServiceError("Service stopped"),
    context={
        "service_name": "my_service"
    }
)
```

### 2. データベース接続修復 (`repair_database_connection`)

```python
repair_result = self_healing.auto_repair(
    error=DatabaseError("Connection failed"),
    context={
        "db_type": "sqlite",
        "db_path": "data/memory.db"
    }
)
```

### 3. Obsidian接続修復 (`repair_obsidian_connection`)

```python
repair_result = self_healing.auto_repair(
    error=ObsidianError("Vault not found"),
    context={
        "vault_path": "C:/Users/mana4/OneDrive/Desktop/Obsidian/ManaOS"
    }
)
```

### 4. ネットワーク再接続 (`reconnect_network`)

```python
repair_result = self_healing.auto_repair(
    error=ConnectionError("Network unreachable"),
    context={
        "url": "http://127.0.0.1:5678",
        "host": "localhost",
        "port": 5678
    }
)
```

### 5. ネットワークパス切り替え (`switch_network_path`)

```python
repair_result = self_healing.auto_repair(
    error=ConnectionError("Primary URL failed"),
    context={
        "primary_url": "http://primary.example.com",
        "fallback_urls": [
            "http://fallback1.example.com",
            "http://fallback2.example.com"
        ]
    }
)
```

### 6. 設定ファイル修復 (`repair_config_file`)

```python
repair_result = self_healing.auto_repair(
    error=ConfigError("Invalid config"),
    context={
        "config_path": "config.json",
        "default_config": {
            "timeout": 30,
            "retry_count": 3
        }
    }
)
```

### 7. リソース不足修復 (`repair_resource_shortage`)

```python
# メモリ不足
repair_result = self_healing.auto_repair(
    error=MemoryError("Out of memory"),
    context={
        "resource_type": "memory"
    }
)

# ディスク不足
repair_result = self_healing.auto_repair(
    error=OSError("No space left"),
    context={
        "resource_type": "disk"
    }
)

# CPU過負荷
repair_result = self_healing.auto_repair(
    error=RuntimeError("CPU overload"),
    context={
        "resource_type": "cpu"
    }
)
```

### 8. タイムアウト設定調整 (`adjust_timeout`)

```python
repair_result = self_healing.auto_repair(
    error=TimeoutError("Request timeout"),
    context={
        "service_name": "my_service",
        "current_timeout": 30,
        "timeout_config_path": "manaos_timeout_config.json"
    }
)
```

---

## 📊 修復統計の取得

### 修復統計を取得

```python
stats = self_healing.get_repair_statistics()

print(f"総修復回数: {stats['total_repairs']}")
print(f"成功回数: {stats['successful_repairs']}")
print(f"失敗回数: {stats['failed_repairs']}")
print(f"成功率: {stats['overall_success_rate']*100:.1f}%")

# アクション別の統計
for action_name, action_stats in stats['action_statistics'].items():
    print(f"{action_name}: 成功率 {action_stats['success_rate']*100:.1f}%")
```

### 修復履歴を取得

```python
# 最新100件の履歴
history = self_healing.get_repair_history(limit=100)

# 成功した修復のみ
success_history = self_healing.get_repair_history(
    limit=50,
    filter_success=True
)

# 特定のアクションのみ
restart_history = self_healing.get_repair_history(
    limit=50,
    filter_action="restart_service"
)
```

### 修復パターンの分析

```python
analysis = self_healing.analyze_repair_patterns()

# 最も頻繁に発生するエラー
print("最も頻繁なエラー:")
for error in analysis['most_common_errors'][:5]:
    print(f"  - {error['error_type']}: {error['occurrence_count']}回")

# 最も効果的なアクション
print("最も効果的なアクション:")
for action in analysis['most_effective_actions']:
    print(f"  - {action['action']}: 成功率 {action['success_rate']*100:.1f}%")

# 推奨事項
print("推奨事項:")
for rec in analysis['recommendations']:
    print(f"  - {rec['message']}")
```

---

## 🔗 統合オーケストレーターとの統合

### 統合オーケストレーターでの使用

```python
from manaos_integration_orchestrator import ManaOSIntegrationOrchestrator

orchestrator = ManaOSIntegrationOrchestrator()

# 包括的な状態を取得（修復統計・分析を含む）
status = orchestrator.get_comprehensive_status()

# 修復統計
repair_stats = status.get("repair_statistics", {})
print(f"修復成功率: {repair_stats.get('overall_success_rate', 0)*100:.1f}%")

# 修復分析
repair_analysis = status.get("repair_analysis", {})
recommendations = repair_analysis.get("recommendations", [])
for rec in recommendations:
    print(f"推奨: {rec['message']}")
```

---

## ⚙️ 設定

### 設定ファイル (`comprehensive_self_capabilities_config.json`)

```json
{
  "enable_auto_repair": true,
  "enable_auto_optimization": true,
  "enable_auto_adaptation": true,
  "repair_threshold": 3,
  "optimization_interval_minutes": 60
}
```

### 設定項目の説明

- `enable_auto_repair`: 自動修復を有効にするか（デフォルト: `true`）
- `enable_auto_optimization`: 自動最適化を有効にするか（デフォルト: `true`）
- `enable_auto_adaptation`: 自動適応を有効にするか（デフォルト: `true`）
- `repair_threshold`: 修復を実行するエラー発生回数の閾値（デフォルト: `3`）
- `optimization_interval_minutes`: 最適化の実行間隔（分）（デフォルト: `60`）

---

## 📝 使用例

### 例1: サービス停止時の自動修復

```python
from comprehensive_self_capabilities_system import ComprehensiveSelfCapabilitiesSystem

self_healing = ComprehensiveSelfCapabilitiesSystem()

try:
    # サービスを呼び出す
    response = requests.get("http://127.0.0.1:5100/health")
except requests.exceptions.ConnectionError as e:
    # 自動修復を実行
    repair_result = self_healing.auto_repair(
        error=e,
        context={
            "service_name": "intent_router",
            "port": 5100
        }
    )
    
    if repair_result.get("success"):
        # 修復成功、再試行
        response = requests.get("http://127.0.0.1:5100/health")
```

### 例2: データベース接続エラー時の自動修復

```python
import sqlite3
from comprehensive_self_capabilities_system import ComprehensiveSelfCapabilitiesSystem

self_healing = ComprehensiveSelfCapabilitiesSystem()

try:
    conn = sqlite3.connect("data/memory.db")
    conn.execute("SELECT * FROM memories")
except sqlite3.OperationalError as e:
    # データベース修復を実行
    repair_result = self_healing.auto_repair(
        error=e,
        context={
            "db_type": "sqlite",
            "db_path": "data/memory.db"
        }
    )
    
    if repair_result.get("success"):
        # 修復成功、再接続
        conn = sqlite3.connect("data/memory.db")
```

### 例3: メモリ不足時の自動修復

```python
from comprehensive_self_capabilities_system import ComprehensiveSelfCapabilitiesSystem

self_healing = ComprehensiveSelfCapabilitiesSystem()

try:
    # 大量のデータを処理
    data = process_large_data()
except MemoryError as e:
    # リソース不足修復を実行
    repair_result = self_healing.auto_repair(
        error=e,
        context={
            "resource_type": "memory"
        }
    )
    
    if repair_result.get("success"):
        # 修復成功、再試行
        data = process_large_data()
```

---

## 🎯 ベストプラクティス

1. **エラーコンテキストの提供**: 修復アクションを選択するために、できるだけ詳細なコンテキストを提供してください。

2. **修復結果の確認**: 自動修復が成功した場合でも、結果を確認して再試行してください。

3. **修復統計の監視**: 定期的に修復統計を確認し、頻繁に発生するエラーの根本原因を調査してください。

4. **推奨事項の活用**: `analyze_repair_patterns()`の推奨事項を参考に、システムの改善を行ってください。

5. **設定の調整**: システムの特性に応じて、`repair_threshold`などの設定を調整してください。

---

## 📚 関連ドキュメント

- `SELF_HEALING_STATUS.md`: 自己修復機能の現状と完成度
- `comprehensive_self_capabilities_system.py`: 実装コード
- `manaos_integration_orchestrator.py`: 統合オーケストレーター

---

## ✅ まとめ

ManaOSの包括的自己修復システムにより、以下の機能が利用可能になりました：

- ✅ エラーの自動検知・学習・修復
- ✅ データベース/ストレージの自動修復
- ✅ ネットワーク接続の自動修復
- ✅ 設定ファイルの自動修復
- ✅ リソース不足時の自動修復
- ✅ 修復統計・分析機能

**完成度**: 約35% → **約73%**（大幅向上！）








