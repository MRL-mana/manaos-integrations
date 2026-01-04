# GitHub CLI インストールガイド

## Windowsでのインストール方法

### 方法1: wingetを使用（推奨）

```powershell
winget install --id GitHub.cli
```

### 方法2: Scoopを使用

```powershell
scoop install gh
```

### 方法3: Chocolateyを使用

```powershell
choco install gh
```

### 方法4: インストーラーをダウンロード

1. https://github.com/cli/cli/releases/latest にアクセス
2. `gh_*_windows_amd64.msi` をダウンロード
3. インストーラーを実行

## インストール後の設定

### 1. GitHub CLIにログイン

```bash
gh auth login
```

以下の選択肢が表示されます：
- **GitHub.com** を選択
- **HTTPS** を選択
- **Login with a web browser** を選択（推奨）
- 認証コードが表示されるので、ブラウザで認証

### 2. 認証状態の確認

```bash
gh auth status
```

### 3. リポジトリのプライベート設定

```bash
gh repo edit MRL-mana/manaos-integrations --visibility private --accept-visibility-change-consequences
```

## 便利なコマンド

### リポジトリ操作

```bash
# リポジトリ一覧
gh repo list

# リポジトリ情報を表示
gh repo view MRL-mana/manaos-integrations

# リポジトリの可視性を変更
gh repo edit MRL-mana/manaos-integrations --visibility private

# リポジトリを作成
gh repo create <name> --private --description "説明"
```

### イシュー操作

```bash
# イシュー一覧
gh issue list

# イシューを作成
gh issue create --title "タイトル" --body "本文"

# イシューを表示
gh issue view <番号>
```

### プルリクエスト操作

```bash
# PR一覧
gh pr list

# PRを作成
gh pr create --title "タイトル" --body "本文"

# PRを表示
gh pr view <番号>
```

## トラブルシューティング

### 認証エラー

```bash
# 認証を再設定
gh auth login

# 認証トークンを確認
gh auth status
```

### コマンドが見つからない

パスが通っているか確認：
```powershell
$env:Path -split ';' | Select-String "GitHub"
```

## 参考リンク

- GitHub CLI公式ドキュメント: https://cli.github.com/manual/
- GitHub CLIリリース: https://github.com/cli/cli/releases

