# GitHub活用クイックスタート

GitHubを活用するための簡単な手順です。

## 🚀 クイックスタート

### 1. 既存のリポジトリに接続

既にGitHubにリポジトリがある場合:

```bash
python connect_existing_github_repo.py
```

### 2. 新しいリポジトリを作成して接続

**注意**: リポジトリ作成には`repo`スコープが必要です。

#### 方法A: GitHubで手動作成

1. GitHubにログイン
2. https://github.com/new にアクセス
3. リポジトリ名: `manaos-integrations`
4. 説明: `ManaOS外部システム統合モジュール集`
5. Public/Privateを選択
6. "Create repository"をクリック

その後、接続:

```bash
python connect_existing_github_repo.py
```

#### 方法B: トークンに`repo`スコープを追加

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 既存のトークンを編集、または新しいトークンを作成
3. `repo`スコープにチェック
4. `.env`ファイルの`GITHUB_TOKEN`を更新
5. 再度実行:

```bash
python setup_github_repo.py
```

## 📝 日常的な使い方

### 変更をコミット・プッシュ

```python
from github_helper import GitHubHelper

helper = GitHubHelper()
helper.auto_commit("機能追加: 新機能の説明")
helper.auto_push()
```

### GitHubと同期

```python
from github_helper import GitHubHelper

helper = GitHubHelper()
helper.sync_with_github("MRL-mana", "manaos-integrations", "main")
```

### リポジトリ情報を取得

```python
from github_integration import GitHubIntegration

github = GitHubIntegration()
repo_info = github.get_repository("MRL-mana", "manaos-integrations")
print(f"スター数: {repo_info['stars']}")
```

### イシューを作成

```python
from github_integration import GitHubIntegration

github = GitHubIntegration()
issue = github.create_issue(
    owner="MRL-mana",
    repo="manaos-integrations",
    title="バグ修正: エラーハンドリング",
    body="詳細な説明...",
    labels=["bug"]
)
```

## 🔧 トラブルシューティング

### 403エラー（リポジトリ作成時）

トークンに`repo`スコープがありません。上記の「方法B」を参照してください。

### プッシュエラー

リモートが設定されていない可能性があります:

```bash
git remote -v
```

設定されていない場合:

```bash
git remote add origin https://github.com/MRL-mana/manaos-integrations.git
```

## 📚 詳細ドキュメント

- `GITHUB_USAGE_GUIDE.md`: 包括的な活用ガイド
- `GITHUB_INTEGRATION_STATUS.md`: 統合ステータス






















