# STEP2: Google Drive認証 クイックスタート

レミ提案の**STEP2（余裕ある日）**を実装するためのガイド。

---

## 🎯 目標

**「生成 → 保存 → Obsidian記録 → Slack通知」が1本通る状態を作る**

- ✅ Google Drive認証
- ✅ n8nで自動化ワークフロー構築
- ✅ 生成物の自動保存・記録・通知

---

## 📋 前提条件

- ✅ STEP1完了（ComfyUI起動、CivitAI API設定）
- ✅ Googleアカウント（まなアカウント）
- ✅ Google Cloud Consoleへのアクセス権限

---

## 🚀 手順

### ステップ1: Google Drive認証

#### 方法A: 自動セットアップスクリプトを使用（推奨）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\setup_google_drive.ps1
```

このスクリプトが以下を自動実行します:
- 認証情報ファイルの確認
- 依存関係の確認・インストール
- Google Drive認証の実行

#### 方法B: 手動セットアップ

1. **Google Cloud Consoleで認証情報を作成**
   - [Google Cloud Console](https://console.cloud.google.com/)にアクセス
   - プロジェクトを作成
   - Google Drive APIを有効化
   - OAuth 2.0認証情報を作成（デスクトップアプリ）
   - `credentials.json`をダウンロード

2. **認証情報ファイルを配置**
   ```powershell
   # credentials.jsonを以下の場所に配置
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations\credentials.json
   ```

3. **認証を実行**
   ```powershell
   python -c "from google_drive_integration import GoogleDriveIntegration; GoogleDriveIntegration()"
   ```

**詳細:** `GOOGLE_DRIVE_SETUP.md`を参照

---

### ステップ2: 動作確認

```powershell
# 統合APIサーバーが起動している状態で
python test_api_endpoints.py
```

または直接確認:
```powershell
python -c "from google_drive_integration import GoogleDriveIntegration; gd = GoogleDriveIntegration(); print('利用可能' if gd.is_available() else '利用不可')"
```

---

### ステップ3: n8nワークフロー構築（次のステップ）

Google Drive認証が完了したら:

1. **n8nでワークフローを作成**
   - トリガー: Webhook（統合APIサーバーから）
   - アクション1: ComfyUI画像生成
   - アクション2: Google Driveに保存
   - アクション3: Obsidianに記録
   - アクション4: Slack通知

2. **統合APIサーバーと連携**
   - n8nのWebhook URLを統合APIサーバーに設定
   - 画像生成完了時にn8nに通知

---

## ✅ 成功の確認

以下のすべてが✅になれば成功:

1. ✅ Google Drive認証が完了
   ```powershell
   # token.jsonが作成されている
   Test-Path "C:\Users\mana4\OneDrive\Desktop\manaos_integrations\token.json"
   ```

2. ✅ Google Drive統合が動作
   ```powershell
   # 統合APIサーバーで確認
   Invoke-RestMethod -Uri "http://127.0.0.1:9510/api/integrations/status" -Method GET
   # google_drive.available = true
   ```

3. ✅ ファイルアップロードが動作
   ```powershell
   $body = @{
       file_path = "C:\path\to\test.png"
   } | ConvertTo-Json

   Invoke-RestMethod -Uri "http://127.0.0.1:9510/api/google_drive/upload" `
       -Method POST `
       -Body $body `
       -ContentType "application/json"
   ```

---

## 🔧 トラブルシューティング

### credentials.jsonが見つからない

```powershell
# ファイルの場所を確認
Get-ChildItem -Path "C:\Users\mana4\OneDrive\Desktop\manaos_integrations" -Filter "credentials.json" -Recurse
```

### 認証エラー

1. Google Drive APIが有効になっているか確認
2. OAuth同意画面でスコープが正しく設定されているか確認
3. テストユーザーに自分のアカウントが追加されているか確認

### 依存関係エラー

```powershell
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

## 📝 次のステップ（STEP3）

STEP2が完了したら:

1. Mem0導入
2. 「マナの判断・好み・失敗」をAIが覚えて先回りする世界
3. ManaOSが**人格OS**になる瞬間

---

## 🔗 関連ファイル

- `setup_google_drive.ps1` - Google Drive認証セットアップスクリプト
- `GOOGLE_DRIVE_SETUP.md` - Google Drive詳細セットアップガイド
- `test_api_endpoints.py` - APIエンドポイントテスト
- `unified_api_server.py` - 統合APIサーバー



















