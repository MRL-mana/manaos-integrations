# 📖 ManaOS 使用ガイド

**バージョン**: 1.0.0  
**最終更新**: 2026-01-04

---

## 📋 目次

1. [はじめに](#はじめに)
2. [インストール](#インストール)
3. [基本設定](#基本設定)
4. [APIの使用](#apiの使用)
5. [セキュリティ設定](#セキュリティ設定)
6. [GPUリソース管理](#gpuリソース管理)
7. [キャッシュシステム](#キャッシュシステム)
8. [バックアップシステム](#バックアップシステム)
9. [メトリクス収集](#メトリクス収集)
10. [トラブルシューティング](#トラブルシューティング)

---

## はじめに

ManaOS統合システムは、複数のサービスとシステムを統合管理するためのプラットフォームです。

### 主な機能

- ✅ 11のコアサービス統合
- ✅ LLMルーティングと最適化
- ✅ 自己修復・自己進化・自己保護・自己管理システム
- ✅ GPUリソース管理
- ✅ インテリジェントキャッシュ
- ✅ 自動バックアップ
- ✅ メトリクス収集

---

## インストール

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env`ファイルを作成：

```bash
# セキュリティ
MANAOS_ENABLE_API_AUTH=true
MANAOS_API_KEY=your-api-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# GPU管理
GPU_MAX_CONCURRENT=2

# バックアップ
BACKUP_SCHEDULE_TIME=02:00
BACKUP_RETENTION_DAYS=30

# LLM設定
OLLAMA_URL=http://127.0.0.1:11434

# ログレベル
LOG_LEVEL=INFO
```

---

## 基本設定

### 設定ファイルの検証

起動前に設定ファイルを検証：

```python
from config_validator_enhanced import get_config_validator

validator = get_config_validator()
results = validator.validate_all_configs()

for config_path, (is_valid, errors) in results.items():
    if not is_valid:
        print(f"❌ {config_path}:")
        for error in errors:
            print(f"  - {error.field}: {error.message}")
```

---

## APIの使用

### 基本リクエスト

```python
import requests

headers = {
    "X-API-Key": "your-api-key-here",
    "Content-Type": "application/json"
}

# ヘルスチェック
response = requests.get("http://127.0.0.1:5000/health", headers=headers)
print(response.json())

# LLMチャット
data = {
    "input_text": "こんにちは",
    "mode": "auto"
}
response = requests.post(
    "http://127.0.0.1:5000/api/llm/chat",
    json=data,
    headers=headers
)
print(response.json())
```

### JWT認証の使用

```python
from manaos_security import JWTManager

# トークン生成
jwt_manager = JWTManager()
token = jwt_manager.generate_token("user123", expires_in=3600)

# リクエスト
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
response = requests.get("http://127.0.0.1:5000/api/services/status", headers=headers)
```

---

## セキュリティ設定

### APIキー認証の有効化

```python
from flask import Flask
from manaos_security import SecurityConfig, require_api_key

app = Flask(__name__)

# セキュリティ設定を適用
security_config = SecurityConfig()
security_config.apply_security(app)

# エンドポイントに認証を追加
@app.route('/api/protected')
@require_api_key
def protected_endpoint():
    return {"message": "認証成功"}
```

### レート制限の設定

```python
from manaos_security import rate_limit

@app.route('/api/endpoint')
@rate_limit(limit_type='strict')  # 60秒間に20リクエスト
def endpoint():
    return {"message": "OK"}
```

### 入力検証

```python
from manaos_security import validate_input

@app.route('/api/endpoint', methods=['POST'])
@validate_input({"input_text": str, "mode": str})
def endpoint():
    data = request.get_json()
    return {"message": "検証成功"}
```

---

## GPUリソース管理

### 基本的な使用

```python
from gpu_resource_manager import get_gpu_manager, GPURequest

manager = get_gpu_manager(max_concurrent=2)

# リクエストを作成
request = GPURequest(
    request_id="req1",
    process_id=123,
    model_name="qwen2.5:7b",
    priority=5
)

# GPUリソースを取得
async with GPUContext(manager, request):
    # GPUを使用した処理
    result = await process_with_gpu()
```

### ステータス確認

```python
status = await manager.get_status()
print(f"アクティブなリクエスト: {status['active_requests']}")
print(f"待機中のリクエスト: {status['waiting_requests']}")
```

---

## キャッシュシステム

### 基本的な使用

```python
from intelligent_cache import get_cache

cache = get_cache(max_size=1000, default_ttl=3600)

# キャッシュに保存
cache.set("key", "value", ttl=3600)

# キャッシュから取得
value = cache.get("key")

# 統計情報
stats = cache.get_stats()
print(f"ヒット率: {stats['hit_rate']:.2%}")
```

### デコレータの使用

```python
from intelligent_cache import cached

@cached(ttl=3600)
def expensive_function(arg1, arg2):
    # 重い処理
    return result
```

---

## バックアップシステム

### 手動バックアップ

```python
from auto_backup_system import get_backup_system

backup_system = get_backup_system()

# バックアップ作成
result = backup_system.create_backup(target_type="all")
print(f"バックアップパス: {result['backup_path']}")
```

### スケジュールバックアップ

```python
# 毎日02:00に自動バックアップ
backup_system.start_scheduled_backups("02:00")
```

### バックアップ一覧

```python
backups = backup_system.list_backups()
for backup in backups:
    print(f"{backup['name']}: {backup['size_mb']:.2f}MB")
```

### バックアップから復元

```python
restore_result = backup_system.restore_backup("backups/20260104_020000")
if restore_result["success"]:
    print("復元成功")
```

---

## メトリクス収集

### 基本的な使用

```python
from metrics_collector import get_metrics_collector

collector = get_metrics_collector()

# カウンター
collector.increment("requests.total")

# ゲージ
collector.set_gauge("system.cpu.percent", 45.5)

# ヒストグラム
collector.record_histogram("response.time", 0.123)

# システムメトリクス収集
collector.collect_system_metrics()
```

### メトリクスの取得

```python
# 統計情報
stats = collector.get_statistics("response.time")
print(f"平均: {stats['avg']:.3f}秒")

# サマリー
summary = collector.get_summary()
print(f"総メトリクス数: {summary['total_metrics']}")
```

---

## トラブルシューティング

### よくある問題

#### 1. API認証エラー

**問題**: `401 Unauthorized`エラー

**解決方法**:
- APIキーが正しく設定されているか確認
- リクエストヘッダーに`X-API-Key`が含まれているか確認

```python
headers = {"X-API-Key": os.getenv("MANAOS_API_KEY")}
```

#### 2. GPUリソース不足

**問題**: GPUリクエストが待機状態になる

**解決方法**:
- 同時実行数を調整
- 優先度を上げる
- 古いリクエストをクリーンアップ

```python
await manager.cleanup_stale_requests()
```

#### 3. キャッシュヒット率が低い

**問題**: キャッシュヒット率が50%未満

**解決方法**:
- キャッシュサイズを増やす
- TTLを調整
- キャッシュを最適化

```python
cache.optimize()
```

#### 4. バックアップ失敗

**問題**: バックアップが作成できない

**解決方法**:
- ディスク容量を確認
- バックアップディレクトリの権限を確認
- ログを確認

```python
result = backup_system.create_backup()
if result.get("errors"):
    print(result["errors"])
```

---

## 詳細ドキュメント

- [API仕様書](docs/openapi.json)
- [トラブルシューティングガイド](TROUBLESHOOTING_GUIDE.md)
- [アーキテクチャドキュメント](ARCHITECTURE.md)

---**最終更新**: 2026-01-04