# Google Drive API セットアップガイド

## 🎯 目標

Google Drive APIを認証して、ManaOS統合APIサーバーからファイルアップロード・管理ができるようにする。

---

## 📋 前提条件

- ✅ Googleアカウント（まなアカウント）
- ✅ Google Cloud Consoleへのアクセス権限

---

## 🚀 セットアップ手順

### ステップ1: Google Cloud Consoleでの設定

#### 1-1. プロジェクトの作成

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
3. プロジェクト名を設定（例: "ManaOS-Drive"）

#### 1-2. Google Drive APIの有効化

1. 左側メニューから「APIとサービス」→「ライブラリ」を選択
2. 「Google Drive API」を検索
3. 「有効にする」をクリック

#### 1-3. OAuth 2.0認証情報の作成

1. 「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「OAuth クライアント ID」を選択
3. アプリケーションの種類: **「デスクトップアプリ」**を選択
4. 名前を設定（例: "ManaOS Drive Client"）
5. 「作成」をクリック
6. 表示された認証情報をダウンロード（JSON形式）
7. ダウンロードしたファイルを `credentials.json` として保存

#### 1-4. OAuth同意画面の設定

1. 「OAuth同意画面」を選択
2. ユーザータイプ: **「外部」**を選択（個人アカウントの場合）
3. アプリ名、ユーザーサポートメール、デベロッパーの連絡先情報を入力
4. スコープを追加:
   - `https://www.googleapis.com/auth/drive.file`（ファイル作成・編集）
   - または `https://www.googleapis.com/auth/drive`（フルアクセス）
5. テストユーザーに自分のGoogleアカウントを追加（開発中の場合）

---

### ステップ2: 認証情報ファイルの配置

1. ダウンロードした `credentials.json` を以下の場所に配置:
   ```
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations\credentials.json
   ```

2. ファイルの存在確認:
   ```powershell
   Test-Path "C:\Users\mana4\OneDrive\Desktop\manaos_integrations\credentials.json"
   ```

---

### ステップ3: 初回認証の実行

#### 方法A: 統合APIサーバー経由（推奨）

```powershell
# 統合APIサーバーが起動している状態で
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python -c "from google_drive_integration import GoogleDriveIntegration; gd = GoogleDriveIntegration(); print('認証完了' if gd.is_available() else '認証が必要')"
```

#### 方法B: 直接実行

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python -c "from google_drive_integration import GoogleDriveIntegration; GoogleDriveIntegration()"
```

**初回実行時:**
1. ブラウザが自動的に開きます
2. Googleアカウントでログイン
3. アプリへのアクセス許可を承認
4. 認証が完了すると `token.json` が作成されます

---

### ステップ4: 動作確認

```powershell
# 統合APIサーバーが起動している状態で
python test_api_endpoints.py
```

または直接確認:
```powershell
python -c "from google_drive_integration import GoogleDriveIntegration; gd = GoogleDriveIntegration(); print('利用可能' if gd.is_available() else '利用不可')"
```

---

## 🔧 トラブルシューティング

### 認証情報ファイルが見つからない

```powershell
# ファイルの場所を確認
Get-ChildItem -Path "C:\Users\mana4\OneDrive\Desktop\manaos_integrations" -Filter "credentials.json" -Recurse
```

### 認証エラーが発生する場合

1. `credentials.json` が正しい場所にあるか確認
2. Google Drive APIが有効になっているか確認
3. OAuth同意画面でスコープが正しく設定されているか確認
4. テストユーザーに自分のアカウントが追加されているか確認（開発中の場合）

### トークンの有効期限切れ

```powershell
# token.jsonを削除して再認証
Remove-Item "C:\Users\mana4\OneDrive\Desktop\manaos_integrations\token.json" -ErrorAction SilentlyContinue
# 再度認証を実行
```

### 依存関係が不足している場合

```powershell
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

## 📝 使用方法

### 統合APIサーバー経由

```powershell
# ファイルをアップロード
$body = @{
    file_path = "C:\path\to\file.png"
    folder_id = ""  # オプション: フォルダID
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:9502/api/google_drive/upload" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

### Pythonコードから直接使用

```python
from google_drive_integration import GoogleDriveIntegration

# 初期化
drive = GoogleDriveIntegration()

# ファイルをアップロード
if drive.is_available():
    file_id = drive.upload_file("path/to/file.png")
    print(f"アップロード完了: {file_id}")
```

---

## 🔗 関連ファイル

- `google_drive_integration.py` - Google Drive統合モジュール
- `unified_api_server.py` - 統合APIサーバー
- `test_api_endpoints.py` - APIエンドポイントテスト

---

## 💡 次のステップ

Google Drive認証が完了したら:

1. ✅ n8nで自動化ワークフロー構築
2. ✅ 生成 → 保存 → Obsidian記録 → Slack通知
3. ✅ バックアップ自動化

---

## 📚 参考リンク

- [Google Drive API ドキュメント](https://developers.google.com/drive/api)
- [OAuth 2.0 設定ガイド](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)



















