# n8n ローカルインストール（母艦）

母艦（新PC）でn8nを動かす場合の手順です。

## 前提条件

- Node.js がインストールされていること（v18以上推奨）

## インストール方法

### 方法1: 自動インストールスクリプト（推奨）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\install_n8n_local.ps1
```

### 方法2: 手動インストール

```powershell
# n8nをグローバルにインストール
npm install -g n8n

# n8nを起動
n8n start
```

## アクセス

ブラウザで以下のURLを開いてください：
```
http://localhost:5678
```

## 設定

### ポートを変更する場合

```powershell
# 環境変数でポートを指定
$env:N8N_PORT = "5679"
n8n start --port 5679
```

### データディレクトリを変更する場合

```powershell
$env:N8N_USER_FOLDER = "C:\path\to\n8n\data"
n8n start
```

## 初回セットアップ

1. ブラウザで `http://localhost:5678` を開く
2. 初回アクセス時にアカウント作成画面が表示されます
3. ユーザー名、メールアドレス、パスワードを入力
4. ログイン後、Settings → API からAPIキーを作成

## APIキーの取得

1. 左上のメニュー（≡）をクリック
2. **Settings** を選択
3. **API** を選択
4. **Create API Key** をクリック
5. APIキー名を入力（例: `MCP Server API`）
6. **Create** をクリック
7. 表示されたAPIキーをコピー

## MCP設定の更新

ローカルでn8nを動かす場合、MCP設定を更新してください：

```powershell
# MCP設定ファイルを編集
notepad "$env:USERPROFILE\.cursor\mcp.json"
```

以下の部分を更新：

```json
"n8n": {
  "env": {
    "N8N_BASE_URL": "http://localhost:5678",
    "N8N_API_KEY": "ここにAPIキーを貼り付け"
  }
}
```

## このはサーバーとの違い

| 項目 | このはサーバー | 母艦（ローカル） |
|------|---------------|-----------------|
| アクセスURL | http://100.93.120.33:5678 | http://localhost:5678 |
| インストール方法 | Docker | npm |
| データ保存場所 | Dockerボリューム | `%USERPROFILE%\.n8n` |
| 起動方法 | `docker start trinity-n8n` | `n8n start` |

## トラブルシューティング

### ポート5678が使用中

```powershell
# 別のポートを使用
$env:N8N_PORT = "5679"
n8n start --port 5679
```

### Node.jsがインストールされていない

1. https://nodejs.org/ からNode.jsをダウンロード
2. インストール後、PowerShellを再起動
3. `node --version` で確認

### n8nが起動しない

```powershell
# ログを確認
n8n start --log-level=debug

# データディレクトリを確認
Get-ChildItem "$env:USERPROFILE\.n8n"
```

## メリット・デメリット

### 母艦で動かすメリット

- ローカルアクセスが速い
- 設定変更が簡単
- デバッグがしやすい

### 母艦で動かすデメリット

- PCを起動していないと使えない
- リソース（メモリ、CPU）を消費する
- このはサーバーとの同期が必要

## 推奨構成

- **開発・テスト**: 母艦でローカル実行
- **本番・常時稼働**: このはサーバーでDocker実行















