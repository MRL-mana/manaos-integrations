# Google Drive クイックセットアップ（5分で完了）

## 🎯 最短手順

### ステップ1: Google Cloud Consoleで認証情報を作成（3分）

1. **Google Cloud Consoleにアクセス**
   - https://console.cloud.google.com/
   - まなアカウントでログイン

2. **プロジェクトを作成または選択**
   - 左上部のプロジェクト選択から「新しいプロジェクト」をクリック
   - プロジェクト名: `ManaOS-Drive`（任意）
   - 「作成」をクリック

3. **Google Drive APIを有効化**
   - 左メニュー「APIとサービス」→「ライブラリ」
   - 検索ボックスに「Google Drive API」と入力
   - 「Google Drive API」をクリック
   - 「有効にする」をクリック

4. **OAuth 2.0認証情報を作成**
   - 左メニュー「APIとサービス」→「認証情報」
   - 上部の「認証情報を作成」→「OAuth クライアント ID」をクリック
   - 「同意画面を設定」をクリック（初回のみ）
     - ユーザータイプ: **「外部」**を選択
     - アプリ名: `ManaOS Drive`（任意）
     - ユーザーサポートメール: 自分のメールアドレス
     - デベロッパーの連絡先情報: 自分のメールアドレス
     - 「保存して次へ」をクリック
     - スコープ: 何も追加せず「保存して次へ」
     - テストユーザー: 自分のGoogleアカウントのメールアドレスを追加
     - 「保存して次へ」→「ダッシュボードに戻る」
   - 再度「認証情報を作成」→「OAuth クライアント ID」
   - アプリケーションの種類: **「デスクトップアプリ」**を選択
   - 名前: `ManaOS Drive Client`（任意）
   - 「作成」をクリック
   - 表示されたダイアログで「JSONをダウンロード」をクリック

5. **認証情報ファイルを配置**
   - ダウンロードしたJSONファイルを `credentials.json` にリネーム
   - 以下の場所に配置:
     ```
     C:\Users\mana4\OneDrive\Desktop\manaos_integrations\credentials.json
     ```

---

### ステップ2: 認証を実行（2分）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\setup_google_drive.ps1
```

**実行時の流れ:**
1. ブラウザが自動的に開きます
2. Googleアカウントでログイン
3. 「このアプリは確認されていません」と表示されたら「詳細」→「ManaOS Drive（安全ではないページ）に移動」をクリック
4. 「アクセスを許可」をクリック
5. 認証完了！

---

## ✅ 確認

```powershell
# token.jsonが作成されているか確認
Test-Path "C:\Users\mana4\OneDrive\Desktop\manaos_integrations\token.json"

# 統合APIサーバーで確認（起動している場合）
python -c "from google_drive_integration import GoogleDriveIntegration; gd = GoogleDriveIntegration(); print('利用可能' if gd.is_available() else '利用不可')"
```

---

## 🔧 トラブルシューティング

### 「このアプリは確認されていません」と表示される

- 「詳細」をクリック
- 「ManaOS Drive（安全ではないページ）に移動」をクリック
- これは開発中のアプリなので正常です

### 認証情報ファイルが見つからない

```powershell
# ファイルの場所を確認
Get-ChildItem -Path "C:\Users\mana4\OneDrive\Desktop\manaos_integrations" -Filter "credentials.json"
```

### 依存関係エラー

```powershell
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

## 📝 次のステップ

認証が完了したら:

1. ✅ 統合APIサーバーで動作確認
2. ✅ ファイルアップロードテスト
3. ✅ n8nワークフロー構築

---

**所要時間:** 約5分  
**難易度:** ⭐⭐（簡単）


















