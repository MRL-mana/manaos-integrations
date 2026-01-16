# GitHub活用ガイド

ManaOS統合プロジェクトでGitHubを活用するための包括的なガイドです。

## 📋 目次

1. [初期設定](#初期設定)
2. [リポジトリ作成と接続](#リポジトリ作成と接続)
3. [自動コミット・プッシュ](#自動コミットプッシュ)
4. [GitHub Actions（CI/CD）](#github-actionscicd)
5. [Issues/PR管理](#issuespr管理)
6. [ベストプラクティス](#ベストプラクティス)

---

## 初期設定

### 1. GitHubトークンの取得

1. GitHubにログイン
2. Settings → Developer settings → Personal access tokens → Tokens (classic)
3. "Generate new token" をクリック
4. 必要なスコープを選択:
   - `repo` - リポジトリへの完全アクセス
   - `workflow` - GitHub Actionsの管理
   - `write:packages` - パッケージのアップロード（オプション）
5. トークンをコピー

### 2. 環境変数の設定

#### Windows PowerShell

```powershell
# ユーザー環境変数に設定（永続的）
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "your_token_here", "User")
```

#### .envファイル

`.env`ファイルに追加:

```env
GITHUB_TOKEN=your_token_here
```

### 3. Gitリポジトリの初期化

```bash
# Gitリポジトリを初期化（既に初期化済みの場合はスキップ）
git init
```

---

## リポジトリ作成と接続

### 自動でリポジトリを作成して接続

```python
from github_automation import GitHubAutomation

automation = GitHubAutomation()

# GitHubリポジトリを作成して接続
remote_url = automation.create_and_connect_repo(
    repo_name="manaos-integrations",
    description="ManaOS外部システム統合モジュール",
    private=False
)

if remote_url:
    print(f"✅ リポジトリ作成完了: {remote_url}")
```

### 既存のリポジトリに接続

```python
# 既存のリモートリポジトリに接続
automation.initialize_repo("https://github.com/username/repo.git")
```

---

## 自動コミット・プッシュ

### 基本的な使い方

```python
from github_helper import GitHubHelper

helper = GitHubHelper()

# 変更を自動コミット
helper.auto_commit(message="機能追加: GitHub統合")

# 変更をプッシュ
helper.auto_push(branch="main")
```

### パターン指定でコミット

```python
# 特定のファイルのみコミット
helper.auto_commit(
    message="設定ファイル更新",
    include_patterns=["*.py", "*.md"]
)

# 特定のファイルを除外
helper.auto_commit(
    message="コード更新",
    exclude_patterns=["*.log", "*.db", "__pycache__/"]
)
```

### GitHubと同期

```python
# プル→コミット→プッシュを一括実行
result = helper.sync_with_github(
    owner="username",
    repo="manaos-integrations",
    branch="main"
)

print(f"プル: {result['pull']}, コミット: {result['commit']}, プッシュ: {result['push']}")
```

---

## GitHub Actions（CI/CD）

### CIワークフロー

`.github/workflows/ci.yml`が自動的に設定されています。

**機能:**
- 複数Pythonバージョンでのテスト
- Lintチェック（flake8）
- 自動テスト実行
- ビルドチェック

**トリガー:**
- `push`（main/master/developブランチ）
- `pull_request`（main/master/developブランチ）

### 自動コミットワークフロー

`.github/workflows/auto-commit.yml`が設定されています。

**機能:**
- 毎日午前2時（UTC）に自動実行
- 変更があれば自動コミット・プッシュ

**手動実行:**
GitHubのActionsタブから手動で実行可能

---

## Issues/PR管理

### イシューの作成

```python
from github_integration import GitHubIntegration

github = GitHubIntegration()

# イシューを作成
issue = github.create_issue(
    owner="username",
    repo="manaos-integrations",
    title="バグ修正: GitHub統合エラー",
    body="詳細な説明...",
    labels=["bug", "high-priority"]
)
```

### エラーから自動でイシュー作成

```python
from github_helper import GitHubHelper

helper = GitHubHelper()

try:
    # 何らかの処理
    pass
except Exception as e:
    # エラーから自動でイシューを作成
    issue = helper.create_issue_from_error(
        owner="username",
        repo="manaos-integrations",
        error_message=str(e),
        error_type="RuntimeError",
        labels=["bug", "auto-generated"]
    )
```

### イシュー・PRの取得

```python
# オープンなイシューを取得
issues = github.get_issues(
    owner="username",
    repo="manaos-integrations",
    state="open",
    limit=10
)

# プルリクエストを取得
prs = github.get_pull_requests(
    owner="username",
    repo="manaos-integrations",
    state="open",
    limit=10
)
```

---

## ベストプラクティス

### 1. コミットメッセージ

明確で意味のあるコミットメッセージを使用:

```
✅ 良い例:
- "機能追加: GitHub自動化スクリプト"
- "バグ修正: トークン認証エラー"
- "ドキュメント更新: GitHub活用ガイド"

❌ 悪い例:
- "更新"
- "修正"
- "変更"
```

### 2. ブランチ戦略

- `main` / `master`: 本番環境用
- `develop`: 開発用
- `feature/*`: 新機能開発用
- `fix/*`: バグ修正用

### 3. .gitignoreの管理

機密情報や一時ファイルは必ず`.gitignore`に追加:

```gitignore
# 環境変数
.env
.env.local

# 認証情報
credentials.json
token.json
*.pem

# データベース
*.db
*.sqlite

# ログ
*.log
logs/
```

### 4. 定期的な同期

定期的にGitHubと同期:

```python
# 毎日の自動同期スクリプト
from github_helper import GitHubHelper
import schedule
import time

def sync_daily():
    helper = GitHubHelper()
    helper.sync_with_github("username", "repo", "main")

schedule.every().day.at("02:00").do(sync_daily)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 5. セキュリティ

- **トークンは絶対にコミットしない**
- `.env`ファイルは`.gitignore`に追加
- 環境変数で管理
- 定期的にトークンをローテーション

---

## 🎯 クイックリファレンス

### よく使うコマンド

```bash
# Gitリポジトリの状態確認
git status

# 変更をコミット
git add .
git commit -m "メッセージ"

# プッシュ
git push origin main

# プル
git pull origin main

# ブランチ作成
git checkout -b feature/new-feature
```

### Pythonスクリプト

```python
# リポジトリ作成と接続
from github_automation import GitHubAutomation
automation = GitHubAutomation()
automation.create_and_connect_repo("repo-name")

# 自動コミット・プッシュ
from github_helper import GitHubHelper
helper = GitHubHelper()
helper.auto_commit("メッセージ")
helper.auto_push()

# GitHubと同期
helper.sync_with_github("owner", "repo", "main")
```

---

## 📚 関連ドキュメント

- [GitHub統合ステータス](GITHUB_INTEGRATION_STATUS.md)
- [GitHub統合設定完了](GITHUB_SETUP_COMPLETE.md)
- [GitHub統合詳細](GITHUB_INTEGRATION.md)

---

## 🆘 トラブルシューティング

### トークンエラー

```
❌ GitHub統合の初期化に失敗しました
```

**解決方法:**
1. `GITHUB_TOKEN`環境変数が設定されているか確認
2. トークンが有効か確認
3. 必要なスコープが付与されているか確認

### プッシュエラー

```
❌ 自動プッシュエラー: Permission denied
```

**解決方法:**
1. リモートURLが正しいか確認
2. トークンに`repo`スコープがあるか確認
3. SSHキーが設定されている場合はHTTPS URLを使用

### コミットエラー

```
❌ 自動コミットエラー: nothing to commit
```

**解決方法:**
変更がない場合は正常です。変更があるか確認してください。

---

**GitHubを活用して、より効率的な開発を！** 🚀






















