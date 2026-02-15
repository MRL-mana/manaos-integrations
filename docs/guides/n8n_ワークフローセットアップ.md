# n8nワークフローセットアップガイド

## 🎯 目標

n8nで「生成 → 保存 → Obsidian記録 → Slack通知」の自動化ワークフローを作成

---

## 📋 前提条件

- ✅ n8nが起動している（このはサーバー側: http://100.93.120.33:5678）
- ✅ Google Drive認証完了
- ✅ Obsidian統合設定済み
- ✅ Slack Webhook URL設定済み

---

## 🚀 セットアップ手順

### ステップ1: n8nにアクセス

1. **n8nにアクセス**
   ```
   http://100.93.120.33:5678
   ```
   または
   ```
   http://127.0.0.1:5678（ローカルで起動している場合）
   ```

2. **ログイン**
   - 初回はアカウント作成が必要

---

### ステップ2: ワークフローの作成

#### 方法A: テンプレートをインポート（推奨）

1. **ワークフローテンプレートをインポート**
   - n8nの「Workflows」→「Import from File」
   - `n8n_workflow_template.json`を選択
   - 「Import」をクリック

2. **認証情報を設定**
   - Google Drive API認証情報を設定
   - Obsidian API認証情報を設定
   - Slack API認証情報を設定

#### 方法B: 手動で作成

1. **Webhookトリガーを作成**
   - ノードを追加 → 「Webhook」を選択
   - HTTP Method: POST
   - Path: `comfyui-generated`
   - 「Listen for Test Event」をクリックしてWebhook URLを取得

2. **Google Driveノードを追加**
   - ノードを追加 → 「Google Drive」を選択
   - Operation: Upload File
   - 認証情報を設定

3. **Obsidianノードを追加**
   - ノードを追加 → 「Obsidian」を選択
   - Operation: Create Note
   - 認証情報を設定

4. **Slackノードを追加**
   - ノードを追加 → 「Slack」を選択
   - Operation: Send Message
   - 認証情報を設定

---

### ステップ3: Webhook URLを取得

1. **Webhookノードを開く**
2. **「Listen for Test Event」をクリック**
3. **表示されたWebhook URLをコピー**
   ```
   http://100.93.120.33:5678/webhook/comfyui-generated
   ```

---

### ステップ4: 環境変数に設定

```powershell
# 環境変数に設定
$env:N8N_WEBHOOK_URL = "http://100.93.120.33:5678/webhook/comfyui-generated"

# または統合APIサーバー起動時に設定
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
$env:N8N_WEBHOOK_URL = "http://100.93.120.33:5678/webhook/comfyui-generated"
python unified_api_server.py
```

---

### ステップ5: ワークフローを有効化

1. **n8nでワークフローを開く**
2. **右上の「Active」スイッチをON**
3. **「Save」をクリック**

---

## ✅ 動作確認

### テスト実行

```powershell
# 統合APIサーバーから画像生成を実行
$body = @{
    prompt = "a beautiful landscape, mountains, sunset, highly detailed"
    width = 512
    height = 512
    steps = 20
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:9502/api/comfyui/generate" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

### 確認項目

1. ✅ n8nのワークフローが実行される
2. ✅ Google Driveにファイルがアップロードされる
3. ✅ Obsidianにノートが作成される
4. ✅ Slackに通知が送信される

---

## 🔧 トラブルシューティング

### n8nに接続できない

- このはサーバー側でn8nが起動しているか確認
- ポート5678が開いているか確認

### Webhookが動作しない

- ワークフローが「Active」になっているか確認
- Webhook URLが正しいか確認
- 統合APIサーバーのログを確認

### 認証エラー

- 各サービスの認証情報が正しく設定されているか確認
- 認証情報の有効期限を確認

---

## 📝 カスタマイズ

### フォルダ構造の変更

Google DriveノードでフォルダIDを指定:
```
ManaOS/Generated/2025/01/28/
```

### 通知メッセージの変更

Slackノードのメッセージをカスタマイズ:
```
🎨 画像生成完了

プロンプト: {{ $json.prompt }}
生成ID: {{ $json.prompt_id }}
```

---

## 🔗 関連ファイル

- `n8n_workflow_template.json` - ワークフローテンプレート
- `n8n_ワークフロー設計.md` - ワークフロー設計
- `unified_api_server.py` - n8n Webhook連携機能

---

**所要時間:** 約10分  
**難易度:** ⭐⭐⭐（中級）



















