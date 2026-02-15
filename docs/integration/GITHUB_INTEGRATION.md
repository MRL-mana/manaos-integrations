# GitHub統合

GitHub APIを使用してリポジトリ情報を取得・操作する機能を実装しました。

## 機能

### ✅ 実装済み機能

1. **リポジトリ情報取得**
   - リポジトリの詳細情報（スター数、フォーク数、言語など）
   - 作成日、更新日、デフォルトブランチなど

2. **コミット履歴取得**
   - 最近のコミット一覧
   - コミットメッセージ、作成者、日時

3. **プルリクエスト取得**
   - オープン/クローズ済みのPR一覧
   - PRの詳細情報

4. **イシュー取得**
   - オープン/クローズ済みのイシュー一覧
   - イシューの詳細情報

5. **リポジトリ検索**
   - キーワードでリポジトリを検索

6. **ユーザーリポジトリ取得**
   - 特定ユーザーのリポジトリ一覧

## セットアップ

### 1. PyGithubのインストール

```bash
pip install PyGithub
```

### 2. GitHubトークンの設定

GitHub Personal Access Tokenを取得して環境変数に設定:

```bash
# Windows PowerShell
$env:GITHUB_TOKEN = "your_github_token_here"

# または .envファイルに追加
GITHUB_TOKEN=your_github_token_here
```

GitHubトークンの取得方法:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token" をクリック
3. 必要なスコープを選択（`repo`, `read:org` など）
4. トークンをコピーして設定

## 使い方

### API経由で使用

#### リポジトリ情報を取得

```bash
curl "http://127.0.0.1:9502/api/github/repository?owner=comfyanonymous&repo=ComfyUI"
```

#### 最近のコミットを取得

```bash
curl "http://127.0.0.1:9502/api/github/commits?owner=comfyanonymous&repo=ComfyUI&branch=main&limit=5"
```

#### プルリクエストを取得

```bash
curl "http://127.0.0.1:9502/api/github/pull_requests?owner=comfyanonymous&repo=ComfyUI&state=open&limit=10"
```

#### リポジトリを検索

```bash
curl "http://127.0.0.1:9502/api/github/search?query=stable+diffusion&limit=10"
```

### Pythonコードから直接使用

```python
from github_integration import GitHubIntegration

github = GitHubIntegration()

# リポジトリ情報取得
repo_info = github.get_repository("comfyanonymous", "ComfyUI")
print(f"スター数: {repo_info['stars']}")

# 最近のコミット取得
commits = github.get_recent_commits("comfyanonymous", "ComfyUI", limit=5)
for commit in commits:
    print(f"{commit['message'][:50]}...")

# プルリクエスト取得
prs = github.get_pull_requests("comfyanonymous", "ComfyUI", state="open")
for pr in prs:
    print(f"PR #{pr['number']}: {pr['title']}")
```

## APIエンドポイント

- `GET /api/github/repository` - リポジトリ情報取得
- `GET /api/github/commits` - コミット履歴取得
- `GET /api/github/pull_requests` - プルリクエスト取得
- `GET /api/github/search` - リポジトリ検索

## 注意事項

- GitHub APIにはレート制限があります（認証済み: 5,000リクエスト/時）
- トークンなしでも一部の情報は取得可能ですが、レート制限が厳しくなります
- プライベートリポジトリにアクセスするには、適切なスコープが必要です



