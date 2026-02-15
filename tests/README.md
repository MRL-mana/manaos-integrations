# ManaOS テストガイド

このディレクトリには、ManaOSの全テストが含まれています。

## ディレクトリ構造

```
tests/
├── unit/           # 単体テスト（高速、独立）
├── integration/    # 統合テスト（API、DB接続）
├── e2e/           # エンドツーエンドテスト（システム全体）
├── performance/   # パフォーマンステスト
└── fixtures/      # テストデータ・フィクスチャ
```

## テスト実行

### すべてのテストを実行

```bash
pytest
```

### カテゴリ別に実行

```bash
# Unit tests のみ
pytest tests/unit -m unit

# Integration tests のみ
pytest tests/integration -m integration

# E2E tests のみ
pytest tests/e2e -m e2e

# Performance tests のみ
pytest tests/performance -m performance
```

### 特定のテストファイルを実行

```bash
pytest tests/unit/test_config_validator_usage.py
```

### 並列実行（高速化）

```bash
pytest -n auto
```

### カバレッジレポート付き

```bash
pytest --cov=. --cov-report=html
# 結果は htmlcov/index.html で確認
```

## テストマーカー

テストには以下のマーカーを付けることができます:

```python
import pytest

@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
def test_api_connection():
    pass

@pytest.mark.slow
@pytest.mark.gpu
def test_gpu_intensive():
    pass

@pytest.mark.external
def test_external_service():
    pass
```

### マーカー一覧

- `unit`: 単体テスト（高速、独立）
- `integration`: 統合テスト（DB、API接続必要）
- `e2e`: エンドツーエンドテスト（システム全体）
- `performance`: パフォーマンステスト
- `slow`: 実行に時間がかかるテスト
- `gpu`: GPU が必要なテスト
- `llm`: LLM モデルが必要なテスト
- `external`: 外部サービスが必要なテスト

## フィクスチャ

共通のセットアップ・クリーンアップロジックは `conftest.py` に定義します。

```python
# tests/conftest.py
import pytest

@pytest.fixture
def test_config():
    """テスト用設定を提供"""
    return {
        'port': 9999,
        'host': '127.0.0.1'
    }

@pytest.fixture(scope="session")
def test_database():
    """テスト用DBセッション"""
    db = create_test_db()
    yield db
    db.close()
```

## ベストプラクティス

### 1. テストは独立させる

```python
# ❌ Bad
state = []

def test_add():
    state.append(1)
    assert len(state) == 1

def test_add_more():
    state.append(2)
    assert len(state) == 2  # 前のテストに依存

# ✅ Good
def test_add():
    state = []
    state.append(1)
    assert len(state) == 1

def test_add_more():
    state = []
    state.append(2)
    assert len(state) == 1
```

### 2. モックを使って外部依存を排除

```python
from unittest.mock import patch, Mock

@patch('requests.post')
def test_api_call(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {'result': 'ok'})
    
    response = call_external_api()
    assert response['result'] == 'ok'
    mock_post.assert_called_once()
```

### 3. パラメータ化でDRYに

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert double(input) == expected
```

### 4. 適切なアサーションメッセージ

```python
# ❌ Bad
assert result == expected

# ✅ Good
assert result == expected, f"Expected {expected}, got {result}"
```

### 5. テスト名は説明的に

```python
# ❌ Bad
def test_1():
    pass

# ✅ Good
def test_unified_api_returns_200_on_valid_request():
    pass
```

## CI/CD 統合

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## トラブルシューティング

### テストが見つからない

```bash
# テストディレクトリを確認
pytest --collect-only

# Python パスを確認
python -c "import sys; print(sys.path)"
```

### ImportError

```bash
# カレントディレクトリをPYTHONPATHに追加
export PYTHONPATH=$PYTHONPATH:$(pwd)

# または pytest.ini で設定（上記参照）
```

### タイムアウト

```bash
# タイムアウトを延長
pytest --timeout=600
```

## 関連リンク

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [ManaOS開発ガイド](../README.md)
