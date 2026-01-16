# GitHubリポジトリセットアップ手順

## 🔒 プライベートリポジトリを作成

### 方法1: GitHubで手動作成（推奨・確実）

1. **GitHubにアクセス**
   - https://github.com/new を開く

2. **リポジトリ情報を入力**
   - Repository name: `manaos-integrations`
   - Description: `ManaOS外部システム統合モジュール集`
   - ⚠️ **必ず「Private」を選択**（重要！）
   - Initialize this repository with: すべて**チェックを外す**（既にローカルにGitリポジトリがあるため）

3. **「Create repository」をクリック**

4. **接続スクリプトを実行**
   ```bash
   python setup_private_repo.py
   ```

### 方法2: GitHub CLIで作成（インストール済みの場合）

```bash
gh repo create manaos-integrations --private --description "ManaOS外部システム統合モジュール集"
```

その後、接続:
```bash
python setup_private_repo.py
```

### 方法3: APIで作成（repoスコープが必要）

1. GitHubトークンに`repo`スコープを追加
2. 実行:
   ```bash
   python setup_github_repo.py
   ```

## ✅ 接続後の確認

リポジトリに接続したら、以下を確認:

```bash
# リモート設定を確認
git remote -v

# プライバシー設定を確認
python check_repo_privacy.py

# 初回プッシュ
git push -u origin master
```

## 📋 チェックリスト

- [ ] リポジトリがプライベートに設定されている
- [ ] `.env`ファイルがコミットされていない
- [ ] 認証情報ファイルがコミットされていない
- [ ] リモートが正しく設定されている

## 🚀 次のステップ

リポジトリに接続したら:

1. **日常的なコミット・プッシュ**
   ```bash
   python github_workflow.py
   ```

2. **自動同期の設定**
   ```python
   from github_helper import GitHubHelper
   helper = GitHubHelper()
   helper.sync_with_github("MRL-mana", "manaos-integrations", "main")
   ```

---

**プライベートリポジトリとして安全に管理しましょう！** 🔒






















