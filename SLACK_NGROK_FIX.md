# Slack ngrok接続修正

## ❌ 問題

ngrok経由でSlack Events APIにアクセスできない（404エラー）

---

## 🔍 原因

ngrok無料版では、初回アクセス時にブラウザ警告ページが表示されます。Slackは警告ページを通過できないため、URL検証が失敗します。

---

## ✅ 解決方法

### 方法1: ngrokの警告を無効化（推奨）

**ngrokを再起動する際に、以下のオプションを追加:**

```powershell
# ngrokを停止
Get-Process ngrok | Stop-Process

# ngrokを再起動（警告無効化オプション付き）
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe http 5114 --host-header=rewrite
```

**または、ngrokの設定ファイルに追加:**

1. **ngrok設定ファイルを開く:**
   ```
   C:\Users\mana4\AppData\Local\ngrok\ngrok.yml
   ```

2. **以下を追加:**
   ```yaml
   version: "2"
   authtoken: YOUR_AUTHTOKEN
   tunnels:
     slack:
       proto: http
       addr: 5114
       inspect: false
   ```

3. **ngrokを起動:**
   ```powershell
   ngrok start slack
   ```

---

### 方法2: ngrokのWeb UIで警告を通過

1. **ブラウザでngrok URLにアクセス:**
   ```
   https://unrevetted-terrie-organometallic.ngrok-free.dev/api/slack/events
   ```

2. **「Visit Site」ボタンをクリック**

3. **Slack Appの設定で「リトライ」をクリック**

---

### 方法3: ngrok有料プランを使用

ngrok有料プランでは警告ページが表示されません。

---

## 🔧 修正内容

Slack Integrationに以下の修正を追加しました:

1. **GETリクエスト対応**: ngrok警告ページ対策
2. **エラーハンドリング強化**: より詳細なログ出力
3. **URL検証時のToken検証スキップ**: 検証フローを改善

---

## 🧪 動作確認

### Step 1: ngrokを再起動（警告無効化オプション付き）

```powershell
Get-Process ngrok | Stop-Process
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe http 5114 --host-header=rewrite
```

### Step 2: Slack Appの設定で「リトライ」

1. **https://api.slack.com/apps にアクセス**
2. **「Event Subscriptions」を開く**
3. **「リトライ」ボタンをクリック**

### Step 3: 検証成功を確認

「Verified」と表示されれば成功です。

---

## 💡 ヒント

- ngrok無料版では、警告ページが表示されることがあります
- `--host-header=rewrite`オプションで警告を回避できます
- 常時利用する場合は、ngrok有料プランを検討してください

---

**ngrokを再起動して、Slack Appの設定で「リトライ」をクリックしてください！**

