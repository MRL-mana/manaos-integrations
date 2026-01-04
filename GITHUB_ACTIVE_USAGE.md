# GitHub活用ガイド - 実践編

GitHubを実際に活用するための具体的な使い方です。

## 🎯 すぐに使える機能

### 1. インタラクティブワークフロー

```bash
python github_workflow.py
```

メニューから操作を選択できます：
- 変更をコミット・プッシュ
- GitHubと同期
- リポジトリ情報を表示
- イシュー一覧を表示
- イシューを作成
- コミット履歴を表示
- リポジトリ検索

### 2. 既存のリポジトリに接続

```bash
python connect_existing_github_repo.py
```

GitHubでリポジトリを作成した後、このスクリプトで接続できます。

### 3. 自動コミット・プッシュ

```python
from github_helper import GitHubHelper

helper = GitHubHelper()
helper.auto_commit("機能追加: 新機能の説明")
helper.auto_push()
```

## 📊 活用例

### リポジトリ情報の監視

```python
from github_integration import GitHubIntegration

github = GitHubIntegration()

# 自分のリポジトリの情報を取得
repo_info = github.get_repository("MRL-mana", "manaos-integrations")
print(f"スター数: {repo_info['stars']}")
print(f"フォーク数: {repo_info['forks']}")
```

### イシューの自動管理

```python
from github_helper import GitHubHelper

helper = GitHubHelper()

# エラーから自動でイシューを作成
try:
    # 何らかの処理
    pass
except Exception as e:
    issue = helper.create_issue_from_error(
        owner="MRL-mana",
        repo="manaos-integrations",
        error_message=str(e),
        error_type="RuntimeError",
        labels=["bug", "auto-generated"]
    )
```

### 定期的な同期

```python
from github_helper import GitHubHelper
import schedule
import time

helper = GitHubHelper()

def sync_daily():
    helper.sync_with_github("MRL-mana", "manaos-integrations", "main")

# 毎日午前2時に同期
schedule.every().day.at("02:00").do(sync_daily)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 🔄 日常的なワークフロー

### 開発フロー

1. **コードを変更**
2. **自動コミット・プッシュ**
   ```bash
   python github_workflow.py
   # メニューから「1. 変更をコミット・プッシュ」を選択
   ```
3. **GitHubで確認**
   - コミット履歴を確認
   - 必要に応じてイシューを作成

### バグ報告フロー

1. **エラーが発生**
2. **自動でイシューを作成**
   ```python
   helper.create_issue_from_error(...)
   ```
3. **GitHubで確認・対応**

## 📈 活用のメリット

1. **バージョン管理**: コードの変更履歴を追跡
2. **バックアップ**: GitHubにコードを保存
3. **コラボレーション**: 他の開発者と共有
4. **イシュー管理**: バグや機能要求を管理
5. **CI/CD**: GitHub Actionsで自動テスト・デプロイ

## 🚀 次のステップ

1. **GitHubリポジトリを作成**
   - GitHubで手動作成、または`connect_existing_github_repo.py`を使用

2. **初回プッシュ**
   ```bash
   python connect_existing_github_repo.py
   ```

3. **日常的に活用**
   ```bash
   python github_workflow.py
   ```

4. **GitHub Actionsを設定**
   - `.github/workflows/ci.yml`が既に設定済み
   - プッシュすると自動でテストが実行されます

## 📚 関連ドキュメント

- `GITHUB_USAGE_GUIDE.md`: 詳細な活用ガイド
- `GITHUB_QUICK_START.md`: クイックスタート
- `GITHUB_INTEGRATION_STATUS.md`: 統合ステータス

---

**GitHubを活用して、より効率的な開発を！** 🚀

