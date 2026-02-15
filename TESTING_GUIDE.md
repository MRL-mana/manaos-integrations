# ManaOS テストスイート実行ガイド

## 📚 テストの種類

ManaOSプロジェクトでは、3層のテストピラミッドを採用しています：

```
        /\
       /E2E\         エンドツーエンドテスト（最も遅い、最も包括的）
      /------\
     /Integration\   統合テスト
    /------------\
   /   Unit Tests  \  ユニットテスト（最も速い、最も多い）
  /----------------\
```

### 1. ユニットテスト（Unit Tests）
- **目的**: 個別関数・クラスの動作を検証
- **実行時間**: 秒単位
- **外部依存**: なし（モック使用）

### 2. 統合テスト（Integration Tests）
- **目的**: 複数コンポーネント間の連携を検証
- **実行時間**: 分単位
- **外部依存**: あり（データベース、Redis等）

### 3. E2Eテスト（End-to-End Tests）
- **目的**: 完全なユーザーワークフローを検証
- **実行時間**: 分単位
- **外部依存**: すべてのサービスが起動している必要あり

## 🚀 クイックスタート

### 前提条件

```bash
# テスト依存関係のインストール
pip install -r requirements-test.txt
```

### 全テスト実行

```bash
# すべてのテストを実行
pytest

# カバレッジ付き
pytest --cov=. --cov-report=html

# HTMLレポート生成
pytest --html=report.html --self-contained-html
```

### テストタイプ別実行

```bash
# ユニットテストのみ
pytest -m unit

# 統合テストのみ
pytest -m integration

# E2Eテストのみ
pytest -m e2e

# 速いテスト（ユニット + 統合）
pytest -m "not e2e and not slow"
```

## 📋 詳細なテスト実行方法

### 1. ユニットテスト

```bash
# 全ユニットテスト
pytest tests/unit/ -v

# 特定ファイルのみ
pytest tests/unit/test_memory_service.py -v

# 特定テスト関数のみ
pytest tests/unit/test_memory_service.py::test_store_memory -v

# 並列実行（高速化）
pytest tests/unit/ -n auto
```

### 2. 統合テスト

```bash
# Dockerサービスを起動
docker-compose up -d postgres redis

# 統合テスト実行
pytest tests/integration/ -v

# 特定のサービス統合テスト
pytest tests/integration/test_mrl_memory_integration.py -v

# クリーンアップ
docker-compose down
```

### 3. E2Eテスト

```bash
# すべてのサービスを起動
docker-compose up -d

# またはローカルで起動
python unified_api_server.py &
python -m mrl_memory_integration &
python -m learning_system_api &
python -m llm_routing_mcp_server &

# E2Eテスト実行
pytest tests/e2e/ -v

# スモークテスト（基本機能のみ）
pytest tests/e2e/ -m smoke -v

# 全ワークフローテスト
pytest tests/e2e/test_full_workflow.py -v
```

## 🔧 高度なテスト実行

### カバレッジレポート

```bash
# HTMLカバレッジレポート生成
pytest --cov=. --cov-report=html

# ブラウザで確認
# htmlcov/index.html を開く

# ターミナルに詳細表示
pytest --cov=. --cov-report=term-missing

# JUnit XMLレポート（CI用）
pytest --junitxml=test-results.xml

# JSONレポート
pytest --json-report --json-report-file=report.json
```

### 並列実行

```bash
# 自動並列実行（CPUコア数に応じて）
pytest -n auto

# 4並列で実行
pytest -n 4

# 分散実行（複数マシン）
pytest -d --tx ssh=user@host1//python --tx ssh=user@host2//python
```

### デバッグモード

```bash
# 詳細出力
pytest -vv

# 最初の失敗で停止
pytest -x

# 失敗したテストのみ再実行
pytest --lf

# 最後に失敗したテストを最初に実行
pytest --ff

# デバッガー起動
pytest --pdb
```

### フィルタリング

```bash
# 特定キーワードを含むテストのみ
pytest -k "memory"

# 複数条件（AND）
pytest -k "memory and store"

# 複数条件（OR）
pytest -k "memory or learning"

# 除外
pytest -k "not slow"

# マーカー組み合わせ
pytest -m "e2e and not slow"
```

## 📊 CI/CD統合

### GitHub Actions

`.github/workflows/ci-cd-pipeline.yml` が既に設定済み：

```yaml
# コード品質チェック
- Syntax check
- Linting (flake8, pylint)
- Type checking (mypy)
- Security scan (bandit, safety)

# テスト実行
- Unit tests (複数OS/Python版)
- Integration tests
- E2E tests
- Performance tests
```

### ローカルでCI/CDシミュレーション

```bash
# コード品質チェック
flake8 . --count --select=E9,F63,F7,F82 --show-source
pylint **/*.py --exit-zero

# 型チェック
mypy . --ignore-missing-imports

# セキュリティスキャン
bandit -r . -f json -o bandit-report.json
safety check

# 全テスト実行（CI相当）
pytest -v --cov=. --cov-report=xml --cov-report=html
```

## 🧪 テスト作成ガイドライン

### ユニットテストの例

```python
import pytest
from mrl_memory_integration import MemoryService

def test_store_memory():
    """メモリ保存のユニットテスト"""
    service = MemoryService()
    
    # テストデータ
    key = "test_key"
    value = {"data": "test"}
    
    # 実行
    result = service.store(key, value)
    
    # 検証
    assert result.success == True
    assert result.key == key

@pytest.mark.asyncio
async def test_async_retrieve():
    """非同期メモリ取得のテスト"""
    service = MemoryService()
    
    # 準備
    await service.async_store("key", "value")
    
    # 実行
    result = await service.async_retrieve("key")
    
    # 検証
    assert result is not None
```

### 統合テストの例

```python
import pytest
import aiohttp

@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_api_integration():
    """メモリAPIの統合テスト"""
    async with aiohttp.ClientSession() as session:
        # 保存
        store_url = "http://localhost:9507/store"
        data = {"key": "integration_test", "value": {"test": "data"}}
        
        async with session.post(store_url, json=data) as response:
            assert response.status == 201
            result = await response.json()
            assert result["success"] == True
        
        # 取得
        retrieve_url = f"http://localhost:9507/retrieve/{data['key']}"
        async with session.get(retrieve_url) as response:
            assert response.status == 200
            result = await response.json()
            assert result["found"] == True
```

### E2Eテストの例

`tests/e2e/test_full_workflow.py` を参照してください。

## 🎯 テストのベストプラクティス

### 1. AAA パターン

```python
def test_example():
    # Arrange（準備）
    service = MyService()
    test_data = {"key": "value"}
    
    # Act（実行）
    result = service.process(test_data)
    
    # Assert（検証）
    assert result.success == True
```

### 2. テストの独立性

```python
@pytest.fixture(autouse=True)
def cleanup():
    """各テスト後にクリーンアップ"""
    yield
    # テスト後の処理
    clean_database()
    clear_cache()
```

### 3. モックの使用

```python
from unittest.mock import patch, MagicMock

@patch('module.external_api_call')
def test_with_mock(mock_api):
    """外部APIをモック"""
    mock_api.return_value = {"status": "ok"}
    
    result = my_function()
    
    mock_api.assert_called_once()
    assert result == expected
```

### 4. パラメータ化テスト

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    """複数入力でテスト"""
    assert double(input) == expected
```

## 🆘 トラブルシューティング

### テストが失敗する

```bash
# 詳細ログ表示
pytest -vv --log-cli-level=DEBUG

# トレースバック表示
pytest --tb=long

# 失敗したテストのみ再実行
pytest --lf -v
```

### サービスが起動しない（E2Eテスト）

```bash
# サービスの状態確認
docker-compose ps

# ログ確認
docker-compose logs unified-api

# ヘルスチェック
curl http://localhost:9502/health
```

### タイムアウトエラー

```bash
# タイムアウト延長
pytest --timeout=600

# 特定テストのみタイムアウト設定
@pytest.mark.timeout(300)
def test_slow_operation():
    pass
```

### カバレッジが低い

```bash
# カバレッジの低いファイル確認
pytest --cov=. --cov-report=term-missing | grep -E "^TOTAL|^.*py.*[0-9]+%"

# 特定モジュールのカバレッジ
pytest --cov=mrl_memory_integration --cov-report=html
```

## 📈 メトリクス目標

- **ユニットテストカバレッジ**: 80%以上
- **統合テストカバレッジ**: 60%以上
- **E2Eテストカバレッジ**: 主要ワークフロー100%
- **テスト実行時間**:
  - ユニット: < 30秒
  - 統合: < 5分
  - E2E: < 10分

## 🔗 関連リンク

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [CI/CDパイプライン](.github/workflows/ci-cd-pipeline.yml)
- [トラブルシューティング](TROUBLESHOOTING.md)

---

Happy Testing! 🧪
