# 🚀 ngrokトンネル作成ガイド

## 🎯 現在の状態

**ngrokがインストール済み** ✅

---

## ✅ 次のステップ

### Step 1: ngrokでトンネルを作成

**n8nのポート5678を公開**:

```powershell
ngrok http 5678
```

**または、バックグラウンドで実行**:

```powershell
Start-Process ngrok -ArgumentList "http 5678"
```

---

### Step 2: URLをコピー

**出力例**:
```
Forwarding  https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:5678
```

**このURLをコピー**:
```
https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
```

**注意**: `xxxx-xxxx-xxxx`の部分は実際のngrok URLに置き換えてください。

---

### Step 3: Browse AIに設定

1. **Browse AIダッシュボードで「統合する」タブを開く**
2. **「Webhooks」または「Add Integration」をクリック**
3. **Webhook URLに以下を入力**:
   ```
   https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
   ```
   （実際のngrok URLに置き換える）
4. **「Save」または「Add」をクリック**

---

## 💡 ヒント

### ngrokを常時起動する場合

**新しいウィンドウで実行**:

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "ngrok http 5678"
```

**これでngrokが別ウィンドウで実行され、閉じても継続します。**

---

### ngrokのURLを確認

**ngrokのWeb UIにアクセス**:
- **ローカル**: http://localhost:4040
- **トンネル情報**: Forwarding URLが表示されます

---

### カスタムドメインを使用する場合（有料プラン）

**カスタムドメインを設定**:

```powershell
ngrok http 5678 --url mydomain.com
```

---

## 🧪 テスト手順

### Step 1: ngrokを起動

```powershell
ngrok http 5678
```

### Step 2: URLをコピー

**出力されたURLをコピー**:
```
https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
```

### Step 3: Browse AIに設定

1. **Browse AIダッシュボード → 統合する → Webhooks**
2. **Webhook URLを設定**
3. **保存**

### Step 4: テスト実行

1. **Browse AIでロボットを実行**
2. **n8nのワークフローでデータを受信**
3. **Slack通知が届くか確認**

---

## 📚 関連ファイル

- `INSTALL_NGROK.md` - ngrokインストールガイド
- `BROWSE_AI_WEBHOOK_SETUP.md` - Webhook設定ガイド

---

**ngrokでトンネルを作成して、Browse AIにWebhook URLを設定してください！**🔥


