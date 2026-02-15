# n8nワークフロー クイックセットアップ（3分で完了）

## 🎯 目標

n8nで「生成 → 保存 → Obsidian記録 → Slack通知」の自動化ワークフローを作成

---

## 🚀 最短手順

### ステップ1: n8nにアクセス（30秒）

1. **ブラウザでn8nを開く**
   ```
   http://100.93.120.33:5678
   ```

2. **ログイン**
   - 初回はアカウント作成が必要

---

### ステップ2: ワークフローをインポート（1分）

1. **「Workflows」→「Import from File」をクリック**
2. **`n8n_workflow_template.json`を選択**
3. **「Import」をクリック**

---

### ステップ3: Webhook URLを取得（30秒）

1. **ワークフローを開く**
2. **Webhookノードをクリック**
3. **「Listen for Test Event」をクリック**
4. **表示されたWebhook URLをコピー**
   ```
   http://100.93.120.33:5678/webhook/comfyui-generated
   ```

---

### ステップ4: 環境変数に設定（30秒）

```powershell
# 統合APIサーバー起動時に設定
$env:N8N_WEBHOOK_URL = "http://100.93.120.33:5678/webhook/comfyui-generated"
```

または、統合APIサーバー起動前に設定:
```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
$env:N8N_WEBHOOK_URL = "http://100.93.120.33:5678/webhook/comfyui-generated"
python unified_api_server.py
```

---

### ステップ5: ワークフローを有効化（30秒）

1. **ワークフローを開く**
2. **右上の「Active」スイッチをON**
3. **「Save」をクリック**

---

## ✅ 完了確認

### テスト実行

```powershell
# 画像生成を実行
$body = @{
    prompt = "a beautiful landscape, mountains, sunset, highly detailed"
    width = 512
    height = 512
    steps = 20
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:9510/api/comfyui/generate" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

### 確認項目

1. ✅ ComfyUIで画像生成が開始される
2. ✅ n8nの実行履歴でワークフローが実行される
3. ✅ Google Driveにファイルがアップロードされる（設定済みの場合）
4. ✅ Obsidianにノートが作成される（設定済みの場合）
5. ✅ Slackに通知が送信される（設定済みの場合）

---

## 🔧 トラブルシューティング

### n8nに接続できない

- このはサーバー側でn8nが起動しているか確認
- ポート5678が開いているか確認

### ワークフローが実行されない

- ワークフローが「Active」になっているか確認
- Webhook URLが正しいか確認
- n8nの実行履歴を確認

---

## 📝 カスタマイズ

### 認証情報の設定

各ノードで認証情報を設定:
- Google Drive: Google Drive API認証情報
- Obsidian: Obsidian API認証情報（必要に応じて）
- Slack: Slack API認証情報（必要に応じて）

### ワークフローのカスタマイズ

- フォルダ構造の変更
- ノート形式の変更
- 通知メッセージの変更

---

**所要時間:** 約3分  
**難易度:** ⭐⭐（簡単）



















