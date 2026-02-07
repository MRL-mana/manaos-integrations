# コントリビューションガイド

ManaOS Integrationsプロジェクトへの貢献を歓迎します！🎉

---

## 📋 目次

- [はじめに](#はじめに)
- [開発環境のセットアップ](#開発環境のセットアップ)
- [コントリビューションの流れ](#コントリビューションの流れ)
- [コーディング規約](#コーディング規約)
- [コミットメッセージ規約](#コミットメッセージ規約)
- [プルリクエストガイドライン](#プルリクエストガイドライン)
- [ドキュメント貢献](#ドキュメント貢献)
- [テストについて](#テストについて)
- [行動規範](#行動規範)

---

## はじめに

### 貢献できること

- 🐛 バグ修正
- ✨ 新機能追加
- 📚 ドキュメント改善
- 🎨 UI/UX改善
- 🧪 テスト追加
- ⚡ パフォーマンス最適化
- 🌍 翻訳（日本語 ↔ 英語）

### 貢献する前に

1. **既存のIssueを確認**: 同じ問題が報告されていないか確認
2. **ディスカッション**: 大きな変更の場合は、事前にIssueで議論
3. **ブランチ戦略**: `master`から分岐して作業

---

## 開発環境のセットアップ

### 1. リポジトリをフォーク

```bash
# GitHubでフォーク後、クローン
git clone https://github.com/YOUR_USERNAME/manaos-integrations.git
cd manaos-integrations

# 元リポジトリをupstreamとして追加
git remote add upstream https://github.com/MRL-mana/manaos-integrations.git
```

### 2. 開発環境構築

```powershell
# Python仮想環境作成 (親フォルダ)
cd ..
python -m venv .venv
.venv\Scripts\Activate.ps1

# 依存関係インストール
cd manaos-integrations
pip install -r requirements-core.txt
pip install -r requirements-dev.txt  # 開発用ツール
```

### 3. VSCodeセットアップ

```powershell
# ワークスペース設定適用
Copy-Item .vscode\settings.json.workspace .vscode\settings.json -Force

# VSCodeで開く
code .
```

推奨拡張機能が自動でインストールされます。

### 4. 動作確認

```powershell
# サービス起動テスト
Ctrl+Shift+B  # またはタスク実行

# ヘルスチェック
python check_services_health.py

# 自動検証
.\validation_script.ps1
```

---

## コントリビューションの流れ

### ステップ1: ブランチ作成

```bash
# 最新のmasterを取得
git fetch upstream
git checkout master
git merge upstream/master

# 作業ブランチを作成
git checkout -b feature/add-new-service
# または
git checkout -b fix/health-check-bug
```

ブランチ命名規則:
- `feature/機能名` - 新機能
- `fix/バグ名` - バグ修正
- `docs/ドキュメント名` - ドキュメント更新
- `refactor/リファクタ内容` - リファクタリング
- `test/テスト内容` - テスト追加

### ステップ2: コードを書く

```python
# 1. 必要な変更を実装
# 2. スニペットを活用（効率化）
#    manaos_init [Tab]
# 3. ドキュメントを更新
```

### ステップ3: コードをテスト

```powershell
# 構文チェック
python -m py_compile your_script.py

# 静的解析（推奨）
flake8 your_script.py
mypy your_script.py

# 動作確認
python your_script.py

# サービスとして起動テスト
python -m your_module
```

### ステップ4: コミット

```bash
git add your_file.py
git commit -m "✨ Add new notification service

- Implement FastAPI-based notification API
- Add health check endpoint
- Update README with usage instructions"
```

[コミットメッセージ規約](#コミットメッセージ規約)を参照。

### ステップ5: プッシュ

```bash
git push origin feature/add-new-service
```

### ステップ6: プルリクエスト作成

1. GitHubでプルリクエストを開く
2. テンプレートに従って記入
3. レビュー待ち

---

## コーディング規約

### Python

#### スタイル: PEP 8準拠

```python
# Good ✅
def calculate_total_price(items: list[dict]) -> float:
    """Calculate the total price of items.
    
    Args:
        items: List of item dictionaries with 'price' key
        
    Returns:
        Total price as float
    """
    return sum(item['price'] for item in items)


# Bad ❌
def calc(x):
    return sum([i['p'] for i in x])
```

#### 型ヒント: 必須

```python
from typing import Optional, Union

def process_data(
    data: dict,
    timeout: Optional[int] = None
) -> Union[dict, None]:
    ...
```

#### ドキュメント文字列: 必須（関数・クラス）

```python
def health_check() -> dict:
    """
    Perform health check on service.
    
    Returns:
        dict: Status information with keys:
            - status: 'healthy' or 'unhealthy'
            - message: Descriptive message
            - timestamp: ISO format timestamp
            
    Raises:
        ConnectionError: If service is unreachable
    """
    ...
```

### ファイル構成

#### サービスファイル構造

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service Name - Brief description

Detailed description of what this service does.
"""

# 標準ライブラリ
import os
import sys
from datetime import datetime

# サードパーティライブラリ
from fastapi import FastAPI, HTTPException
import uvicorn

# ローカルモジュール
from manaos_core import config

# 定数
DEFAULT_PORT = 5000
SERVICE_NAME = "example_service"

# FastAPIアプリ
app = FastAPI(title=SERVICE_NAME)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=DEFAULT_PORT)
```

### コードチェックツール

```powershell
# インストール
pip install flake8 mypy black isort

# 実行
flake8 your_script.py        # 構文チェック
mypy your_script.py          # 型チェック
black your_script.py         # 自動フォーマット
isort your_script.py         # import文ソート
```

---

## コミットメッセージ規約

### フォーマット

```
<絵文字> <タイプ>: <件名>

<本文（オプション）>

<フッター（オプション）>
```

### タイプと絵文字

| 絵文字 | タイプ | 説明 |
|--------|--------|------|
| ✨ | feat | 新機能 |
| 🐛 | fix | バグ修正 |
| 📚 | docs | ドキュメントのみの変更 |
| 🎨 | style | コードの意味に影響しない変更（空白、フォーマットなど） |
| ♻️ | refactor | バグ修正でも機能追加でもないコード変更 |
| ⚡ | perf | パフォーマンス改善 |
| ✅ | test | テストの追加・修正 |
| 🔧 | chore | ビルドプロセスやツールの変更 |
| 🚀 | deploy | デプロイ関連 |
| 🔒 | security | セキュリティ修正 |

### 例

#### 良い例 ✅

```
✨ feat: Add notification service with SMS support

- Implement FastAPI-based notification API
- Add Twilio integration for SMS
- Include health check endpoint
- Update README with configuration instructions

Closes #123
```

```
🐛 fix: Resolve race condition in health check

The health check was failing intermittently due to
a race condition when multiple services started simultaneously.

Added proper locking mechanism to prevent concurrent access.

Fixes #456
```

```
📚 docs: Update VSCODE_SETUP_GUIDE with troubleshooting section

Added common issues and solutions:
- Extension installation failures
- Python interpreter not found
- Task execution errors
```

#### 悪い例 ❌

```
update  # 何を更新したか不明
```

```
fix bug  # どのバグか不明
```

```
add stuff  # 何を追加したか不明
```

---

## プルリクエストガイドライン

### PRテンプレート

```markdown
## 概要
このPRの目的を簡潔に説明してください。

## 変更内容
- 追加した機能や修正した内容を箇条書きで

## 関連Issue
Closes #123

## テスト方法
1. サービスを起動
2. `http://localhost:9500/new-endpoint`にアクセス
3. 期待結果: ...

## スクリーンショット（該当する場合）

## チェックリスト
- [ ] コードは動作確認済み
- [ ] テストを追加/更新した
- [ ] ドキュメントを更新した
- [ ] コミットメッセージは規約に従っている
- [ ] 静的解析ツールでチェック済み
```

### レビュープロセス

1. **自動チェック**: GitHub Actionsが実行される
   - 構文チェック
   - 型チェック
   - ドキュメントリンク検証

2. **コードレビュー**: メンテナーがレビュー
   - 機能の正確性
   - コードの品質
   - ドキュメントの完全性

3. **承認 & マージ**: レビュー通過後、マージ

### レビューコメントへの対応

```bash
# フィードバックに基づいて修正
git add modified_file.py
git commit -m "🔧 Address review comments: improve error handling"
git push origin feature/add-new-service

# PRに自動的に反映される
```

---

## ドキュメント貢献

### ドキュメント種類

| ファイル | 目的 |
|---------|------|
| `README.md` | プロジェクト概要、クイックスタート |
| `VSCODE_SETUP_GUIDE.md` | VSCode完全セットアップ |
| `FAQ.md` | よくある質問 |
| `CONTRIBUTING.md` | このファイル |
| `*.md` in `docs/` | 詳細ガイド |

### ドキュメント記述規則

#### 見出し階層

```markdown
# H1 - ファイルタイトル（1つのみ）

## H2 - セクション

### H3 - サブセクション

#### H4 - 詳細
```

#### コードブロック

````markdown
```python
# Python code with syntax highlighting
def example():
    return "Hello"
```

```powershell
# PowerShell code
Get-Process python
```
````

#### リンク

```markdown
# 内部リンク
[詳細はこちら](#セクション名)

# 外部リンク
[GitHub](https://github.com/MRL-mana/manaos-integrations)

# ファイルリンク
[セットアップガイド](VSCODE_SETUP_GUIDE.md)
```

#### テーブル

```markdown
| 列1 | 列2 | 列3 |
|-----|-----|-----|
| データ1 | データ2 | データ3 |
```

### ドキュメント検証

```powershell
# リンク切れチェック（手動）
# 各ドキュメントのリンクをクリックして確認

# Markdown構文チェック（拡張機能）
# davidanson.vscode-markdownlint を使用
```

---

## テストについて

### テストの種類

1. **ユニットテスト**: 個別機能のテスト
2. **統合テスト**: サービス間連携のテスト
3. **E2Eテスト**: 全体フローのテスト

### テストフレームワーク: pytest

```python
# test_health_check.py
import pytest
from fastapi.testclient import TestClient
from your_service import app

client = TestClient(app)


def test_health_endpoint_returns_200():
    """Health endpoint should return 200 OK"""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_healthy_status():
    """Health endpoint should return healthy status"""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.parametrize("port", [9500, 5103, 5104, 5111])
def test_all_services_are_healthy(port):
    """All services should be healthy"""
    import requests
    response = requests.get(f"http://localhost:{port}/health", timeout=5)
    assert response.status_code == 200
```

### テスト実行

```powershell
# すべてのテストを実行
pytest

# 特定のテストファイル
pytest test_health_check.py

# 特定のテスト関数
pytest test_health_check.py::test_health_endpoint_returns_200

# カバレッジレポート
pytest --cov=. --cov-report=html
```

### テストを追加する場合

1. ファイル名: `test_*.py` または `*_test.py`
2. 関数名: `test_*`
3. クラス名: `Test*`

---

## 行動規範

### 基本原則

- 🤝 **尊重**: すべての人を尊重する
- 🎯 **建設的**: 批判は建設的に
- 🌟 **歓迎**: 初心者も歓迎
- 🔒 **プライバシー**: 個人情報を尊重

### 禁止事項

- ❌ ハラスメント（性的、人種差別など）
- ❌ 攻撃的な言動
- ❌ スパム
- ❌ プライバシー侵害

### 報告

不適切な行動を目撃した場合は、GitHubのIssueまたはPrivate Messageで報告してください。

---

## コントリビューター一覧

貢献者の皆様に感謝します！🙏

<!-- コントリビューターが自動で表示されます -->
<a href="https://github.com/MRL-mana/manaos-integrations/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=MRL-mana/manaos-integrations" />
</a>

---

## 📚 関連リソース

- **[README.md](README.md)** - プロジェクト概要
- **[FAQ.md](FAQ.md)** - よくある質問
- **[VSC ODE_SETUP_GUIDE.md](VSCODE_SETUP_GUIDE.md)** - 開発環境セットアップ
- **[GitHub Issues](https://github.com/MRL-mana/manaos-integrations/issues)** - バグ報告・機能リクエスト

---

## 💡 質問がありますか？

- **Issue**: [新しいIssueを作成](https://github.com/MRL-mana/manaos-integrations/issues/new)
- **Discussion**: [ディスカッションに参加](https://github.com/MRL-mana/manaos-integrations/discussions)

---

**ハッピーコーディング！** 🚀

**最終更新**: 2026年2月7日
