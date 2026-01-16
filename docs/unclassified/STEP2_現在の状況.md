# STEP2: Google Drive認証 現在の状況

**日付:** 2025-01-28  
**ステータス:** 準備完了、認証情報作成待ち

---

## ✅ 完了項目

### 依存関係
- ✅ Google Drive APIライブラリ: インストール済み
  - google-auth: 2.41.1
  - google-auth-oauthlib: 1.2.3
  - google-auth-httplib2: 0.3.0
  - google-api-python-client: 2.187.0

### セットアップスクリプト
- ✅ `setup_google_drive.ps1` - 認証セットアップスクリプト作成済み
- ✅ `check_google_drive_setup.ps1` - 状況確認スクリプト作成済み
- ✅ `GOOGLE_DRIVE_クイックセットアップ.md` - 5分で完了する手順書作成済み

---

## ⚠️ 要対応項目

### 認証情報ファイル（credentials.json）

**現状:** 未配置  
**必要作業:** Google Cloud Consoleで認証情報を作成

**手順:**
1. https://console.cloud.google.com/ にアクセス
2. プロジェクトを作成（または既存を選択）
3. Google Drive APIを有効化
4. OAuth 2.0認証情報を作成（デスクトップアプリ）
5. `credentials.json`をダウンロードして配置

**詳細:** `GOOGLE_DRIVE_クイックセットアップ.md`を参照

---

## 🚀 次のアクション

### ステップ1: 認証情報を作成（約3分）

1. **Google Cloud Consoleにアクセス**
   ```
   https://console.cloud.google.com/
   ```

2. **プロジェクトを作成**
   - 左上部のプロジェクト選択から「新しいプロジェクト」
   - プロジェクト名: `ManaOS-Drive`
   - 「作成」をクリック

3. **Google Drive APIを有効化**
   - 左メニュー「APIとサービス」→「ライブラリ」
   - 「Google Drive API」を検索して「有効にする」

4. **OAuth 2.0認証情報を作成**
   - 「APIとサービス」→「認証情報」
   - 「認証情報を作成」→「OAuth クライアント ID」
   - アプリケーションの種類: **「デスクトップアプリ」**
   - 名前: `ManaOS Drive Client`
   - 「作成」→「JSONをダウンロード」

5. **認証情報ファイルを配置**
   ```powershell
   # ダウンロードしたJSONファイルをリネームして配置
   # 配置先: C:\Users\mana4\OneDrive\Desktop\manaos_integrations\credentials.json
   ```

### ステップ2: 認証を実行（約2分）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\setup_google_drive.ps1
```

---

## 📝 確認コマンド

### 認証情報ファイルの確認

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\check_google_drive_setup.ps1
```

### 認証後の動作確認

```powershell
# token.jsonが作成されているか確認
Test-Path "C:\Users\mana4\OneDrive\Desktop\manaos_integrations\token.json"

# Google Drive統合の動作確認
python -c "from google_drive_integration import GoogleDriveIntegration; gd = GoogleDriveIntegration(); print('利用可能' if gd.is_available() else '利用不可')"
```

---

## 🔗 関連ファイル

- `GOOGLE_DRIVE_クイックセットアップ.md` - 5分で完了する手順書
- `GOOGLE_DRIVE_SETUP.md` - 詳細セットアップガイド
- `setup_google_drive.ps1` - 認証セットアップスクリプト
- `check_google_drive_setup.ps1` - 状況確認スクリプト

---

## 💡 ヒント

- **OAuth同意画面の設定:** 初回のみ必要。外部アプリとして設定し、テストユーザーに自分のアカウントを追加
- **「このアプリは確認されていません」:** 開発中のアプリなので正常。詳細→安全ではないページに移動で進める
- **認証情報ファイル:** `credentials.json`は機密情報なので、Gitにコミットしないこと

---

**進捗:** 準備完了、認証情報作成待ち


















