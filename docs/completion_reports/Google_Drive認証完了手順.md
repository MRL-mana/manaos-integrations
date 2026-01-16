# Google Drive認証完了手順

## ✅ 現在の状況

- ✅ **credentials.json**: このはサーバーからコピー完了
- ⚠️ **token.json**: 再認証が必要

---

## 🚀 認証手順（約1分）

### ステップ1: 認証URLにアクセス

以下のURLをブラウザで開いてください:

```
https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=584570153591-of0k4v23uj7l64spnhuscdqnd4cveboe.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A65059%2F&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file&state=daSW1gNIWuaosbKgD2RY4VlcWeEbiy&access_type=offline
```

または、以下のコマンドで自動的にブラウザが開きます:

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\setup_google_drive.ps1
```

### ステップ2: Googleアカウントでログイン

1. ブラウザでGoogleアカウントにログイン
2. 「このアプリは確認されていません」と表示されたら:
   - 「詳細」をクリック
   - 「ManaOS Drive（安全ではないページ）に移動」をクリック
3. 「アクセスを許可」をクリック

### ステップ3: 認証完了確認

認証が完了すると、`token.json`が自動的に作成されます。

```powershell
# 認証完了を確認
Test-Path "C:\Users\mana4\OneDrive\Desktop\manaos_integrations\token.json"

# Google Drive統合の動作確認
python -c "from google_drive_integration import GoogleDriveIntegration; gd = GoogleDriveIntegration(); print('利用可能' if gd.is_available() else '利用不可')"
```

---

## ✅ 認証完了後

### 動作確認

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\check_google_drive_setup.ps1
```

### 統合APIサーバーで確認

```powershell
# 統合APIサーバーが起動している状態で
python test_api_endpoints.py
```

---

## 💡 ヒント

- **認証URL**: 上記のURLは一時的なものです。期限切れの場合は、`setup_google_drive.ps1`を再実行してください
- **credentials.json**: このはサーバーからコピーしたファイルを使用（問題なし）
- **token.json**: 再認証が必要（スコープが異なるため）

---

**所要時間:** 約1分  
**難易度:** ⭐（簡単）


















