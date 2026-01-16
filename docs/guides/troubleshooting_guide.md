# 🔧 ManaOS トラブルシューティングガイド

**バージョン**: 1.0.0  
**最終更新**: 2026-01-04

---

## 📋 目次

1. [一般的な問題](#一般的な問題)
2. [セキュリティ関連](#セキュリティ関連)
3. [パフォーマンス問題](#パフォーマンス問題)
4. [GPUリソース問題](#gpuリソース問題)
5. [データベース問題](#データベース問題)
6. [ネットワーク問題](#ネットワーク問題)
7. [ログの確認方法](#ログの確認方法)

---

## 一般的な問題

### サービスが起動しない

**症状**: サービスが起動しない、またはすぐに終了する

**確認事項**:
1. ポートが既に使用されていないか確認
```bash
netstat -ano | findstr :5100
```

2. ログファイルを確認
```bash
tail -f logs/unified_api_server.log
```

3. 設定ファイルの検証
```python
from config_validator_enhanced import get_config_validator
validator = get_config_validator()
results = validator.validate_all_configs()
```

**解決方法**:
- ポートが使用中の場合は、別のポートを使用するか、既存のプロセスを終了
- 設定ファイルのエラーを修正
- 依存パッケージがインストールされているか確認

---

### メモリ不足エラー

**症状**: `MemoryError`または`OutOfMemoryError`

**確認事項**:
```python
import psutil
memory = psutil.virtual_memory()
print(f"メモリ使用率: {memory.percent}%")
print(f"利用可能メモリ: {memory.available / 1024 / 1024 / 1024:.2f}GB")
```

**解決方法**:
1. キャッシュサイズを減らす
```python
cache = get_cache(max_size=500)  # 1000から500に減らす
```

2. バックグラウンドプロセスを終了
3. システムリソースを監視
```python
from metrics_collector import get_metrics_collector
collector = get_metrics_collector()
collector.collect_system_metrics()
```

---

## セキュリティ関連

### API認証エラー

**症状**: `401 Unauthorized`エラー

**確認事項**:
1. APIキーが設定されているか確認
```python
import os
print(os.getenv("MANAOS_API_KEY"))
```

2. リクエストヘッダーを確認
```python
headers = {
    "X-API-Key": "your-api-key",
    "Content-Type": "application/json"
}
```

**解決方法**:
- `.env`ファイルに`MANAOS_API_KEY`を設定
- リクエストヘッダーに`X-API-Key`を追加
- APIキーが正しいか確認

---

### レート制限エラー

**症状**: `429 Too Many Requests`エラー

**確認事項**:
```python
from manaos_security import RateLimiter
limiter = RateLimiter()
remaining = limiter.get_remaining("your-identifier")
print(f"残りリクエスト数: {remaining}")
```

**解決方法**:
1. リクエスト頻度を減らす
2. レート制限の設定を調整（開発環境の場合）
3. キャッシュを使用してリクエスト数を減らす

---

## パフォーマンス問題

### レスポンスが遅い

**症状**: APIレスポンスが遅い

**確認事項**:
1. メトリクスを確認
```python
from metrics_collector import get_metrics_collector
collector = get_metrics_collector()
stats = collector.get_statistics("response.time")
print(f"平均レスポンス時間: {stats['avg']:.3f}秒")
```

2. システムリソースを確認
```python
collector.collect_system_metrics()
summary = collector.get_summary()
print(summary)
```

**解決方法**:
1. キャッシュを有効化
```python
from intelligent_cache import cached

@cached(ttl=3600)
def expensive_operation():
    pass
```

2. GPUリソースの競合を確認
3. データベースクエリを最適化

---

### キャッシュヒット率が低い

**症状**: キャッシュヒット率が50%未満

**確認事項**:
```python
cache = get_cache()
stats = cache.get_stats()
print(f"ヒット率: {stats['hit_rate']:.2%}")
```

**解決方法**:
1. キャッシュサイズを増やす
```python
cache = get_cache(max_size=2000)  # 1000から2000に増やす
```

2. TTLを延長
```python
cache.set("key", "value", ttl=7200)  # 1時間から2時間に延長
```

3. キャッシュを最適化
```python
cache.optimize()
```

---

## GPUリソース問題

### GPUリソースが取得できない

**症状**: GPUリクエストが待機状態になる

**確認事項**:
```python
from gpu_resource_manager import get_gpu_manager
manager = get_gpu_manager()
status = await manager.get_status()
print(f"アクティブ: {status['active_requests']}")
print(f"待機中: {status['waiting_requests']}")
```

**解決方法**:
1. 同時実行数を増やす（リソースが十分な場合）
```python
manager = get_gpu_manager(max_concurrent=3)
```

2. 古いリクエストをクリーンアップ
```python
await manager.cleanup_stale_requests()
```

3. 優先度を上げる
```python
request = GPURequest(
    request_id="req1",
    process_id=123,
    model_name="model",
    priority=10  # 1-10、10が最高
)
```

---

### GPUメモリ不足

**症状**: GPUメモリエラー

**確認事項**:
```python
from gpu_resource_manager import get_gpu_manager
manager = get_gpu_manager()
memory_usage = manager.get_gpu_memory_usage()
if memory_usage:
    print(f"GPUメモリ使用率: {memory_usage:.1f}%")
```

**解決方法**:
1. 軽量モデルを使用
2. バッチサイズを減らす
3. 不要なプロセスを終了

---

## データベース問題

### データベース接続エラー

**症状**: `sqlite3.OperationalError`または`psycopg2.OperationalError`

**確認事項**:
1. データベースファイルの存在確認
```python
from pathlib import Path
db_path = Path("revenue_tracker.db")
print(f"データベース存在: {db_path.exists()}")
```

2. データベースの整合性チェック
```python
import sqlite3
conn = sqlite3.connect("revenue_tracker.db")
cursor = conn.cursor()
cursor.execute("PRAGMA integrity_check;")
result = cursor.fetchone()
print(f"整合性チェック: {result}")
```

**解決方法**:
1. バックアップから復元
```python
from auto_backup_system import get_backup_system
backup_system = get_backup_system()
restore_result = backup_system.restore_backup("backups/latest")
```

2. データベースファイルの権限を確認
3. ディスク容量を確認

---

## ネットワーク問題

### タイムアウトエラー

**症状**: `requests.Timeout`または`httpx.TimeoutException`

**確認事項**:
1. タイムアウト設定を確認
```python
from manaos_timeout_config import get_timeout
timeout = get_timeout("api_call")
print(f"タイムアウト設定: {timeout}秒")
```

2. ネットワーク接続を確認
```python
import requests
try:
    response = requests.get("http://localhost:5100/health", timeout=5)
    print(f"接続成功: {response.status_code}")
except Exception as e:
    print(f"接続エラー: {e}")
```

**解決方法**:
1. タイムアウト時間を延長
```python
# manaos_timeout_config.jsonで設定
{
    "api_call": 10.0  # 5秒から10秒に延長
}
```

2. リトライロジックを実装
3. ネットワーク接続を確認

---

## ログの確認方法

### ログファイルの場所

```
logs/
├── unified_api_server.log
├── manaos_integration_orchestrator.log
├── error.log
└── ...
```

### ログの確認

```bash
# 最新のログを確認
tail -f logs/unified_api_server.log

# エラーログを確認
grep ERROR logs/*.log

# 特定のキーワードで検索
grep "GPU" logs/*.log
```

### Pythonからログを確認

```python
from manaos_logger import get_logger
logger = get_logger(__name__)

# ログレベルを変更
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 緊急時の対応

### システムが応答しない場合

1. **プロセスを確認**
```bash
# Windows
tasklist | findstr python

# Linux/Mac
ps aux | grep python
```

2. **強制終了**
```bash
# Windows
taskkill /PID <PID> /F

# Linux/Mac
kill -9 <PID>
```

3. **ログを確認**
```bash
tail -100 logs/error.log
```

### データベースが破損した場合

1. **バックアップから復元**
```python
from auto_backup_system import get_backup_system
backup_system = get_backup_system()
backups = backup_system.list_backups()
# 最新のバックアップを選択
latest_backup = backups[0]
restore_result = backup_system.restore_backup(latest_backup["path"])
```

2. **整合性チェックを実行**
```python
import sqlite3
conn = sqlite3.connect("revenue_tracker.db")
cursor = conn.cursor()
cursor.execute("PRAGMA integrity_check;")
```

---

## サポート

問題が解決しない場合は、以下を確認してください：1. ログファイルを確認
2. 設定ファイルを検証
3. システムリソースを確認
4. ドキュメントを再確認---**最終更新**: 2026-01-04