# ✅ Webhook設定完了

## 🎯 現在の設定

**プロダクションURL**: `http://localhost:5678/webhook/browse-ai-webhook`

**設定内容**:
- ✅ HTTP Method: POST
- ✅ Path: `browse-ai-webhook`
- ✅ Authentication: None
- ✅ Respond: Using 'Respond to Webhook' Node

---

## ✅ 次のステップ

### Step 1: ワークフローを有効化

1. **ワークフローの右上のトグルスイッチをONにする**
2. **Webhookがリッスン中になることを確認**

---

### Step 2: テスト実行

**PowerShellでテスト**:

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\test_browse_ai_webhook.ps1
```

**または、プロダクションURLでテスト**:

```powershell
$webhookUrl = "http://localhost:5678/webhook/browse-ai-webhook"
$body = @{
    robot = @{
        name = "Sale Monitor"
    }
    capturedAt = @{
        url = "https://example.com"
        timestamp = (Get-Date).ToISOString()
    }
    extractedData = @{
        name = "テスト商品"
        price = "1000円"
        discount = "20%"
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json"
```

---

### Step 3: Browse AIに設定（本番環境）

**ローカル開発中は**:
- テストURLを使用して動作確認

**Browse AIから実際のデータを受信するには**:
- ngrokでパブリックURLを取得
- Browse AIに設定

**ngrokの使い方**:
```powershell
ngrok http 5678
```

**出力されたURL**:
```
https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
```

---

## 🧪 テスト手順

### Step 1: ワークフローを有効化

1. **右上のトグルスイッチをON**
2. **Webhookがリッスン中になることを確認**

### Step 2: テスト実行

```powershell
.\test_browse_ai_webhook.ps1
```

### Step 3: 結果確認

- ✅ **n8nのワークフローでデータを受信**
- ✅ **Slack通知が届くか確認**

---

## 📚 関連ファイル

- `test_browse_ai_webhook.ps1` - テストスクリプト
- `BROWSE_AI_WEBHOOK_SETUP.md` - Webhook設定ガイド

---

**設定完了！ワークフローを有効化して、テストを実行してください！**🔥


