# 🔗 Browse AI Webhook設定ガイド

## 🎯 現在の状態

n8nのWebhookノードがテストモードでリッスン中

**テストURL**: `http://localhost:5678/webhook-test/browse-ai-webhook`

---

## ✅ プロダクションURLを取得

### Step 1: プロダクションURLを確認

1. **n8nのWebhookノードを開く**
2. **「プロダクションURL」ボタンをクリック**
3. **表示されるURLをコピー**

**プロダクションURLの形式**:
```
http://localhost:5678/webhook/browse-ai-webhook
```

**注意**: これはローカルURLです。Browse AIからアクセスするには、**パブリックURL**が必要です。

---

## 🌐 パブリックURLを取得（ngrok使用）

### Step 1: ngrokをインストール

```powershell
# Chocolatey経由（推奨）
choco install ngrok

# または直接ダウンロード
# https://ngrok.com/download
```

---

### Step 2: ngrokでトンネルを作成

```powershell
ngrok http 5678
```

**出力例**:
```
Forwarding  https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:5678
```

**このURLをコピー**:
```
https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
```

---

### Step 3: Browse AIに設定

1. **Browse AIダッシュボードにログイン**
2. **ロボットを選択**
3. **「Webhooks」または「Integrations」を開く**
4. **Webhook URLに以下を入力**:
   ```
   https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
   ```
5. **保存**

---

## 🧪 テスト方法

### 方法A: n8nのテスト機能を使用

1. **Webhookノードで「テストURL」をクリック**
2. **左パネルで「模擬データを設定する」をクリック**
3. **テストデータを入力**
4. **「実行」をクリック**

---

### 方法B: PowerShellでテスト

```powershell
$webhookUrl = "http://localhost:5678/webhook-test/browse-ai-webhook"
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

### 方法C: Browse AIから実際のデータを送信

1. **Browse AIでロボットを実行**
2. **n8nのワークフローでデータを受信**
3. **Slack通知が届くか確認**

---

## 💡 ローカル開発の場合

**ローカル開発中は**:
- テストURLを使用: `http://localhost:5678/webhook-test/browse-ai-webhook`
- Browse AIの代わりに、PowerShellやPostmanでテスト

**本番環境では**:
- ngrokでパブリックURLを取得
- Browse AIに設定

---

## 📚 関連ファイル

- `BROWSE_AI_SETUP.md` - Browse AIセットアップガイド
- `test_browse_ai_webhook.ps1` - テストスクリプト

---

**プロダクションURLを確認して、Browse AIに設定してください！**🔥


