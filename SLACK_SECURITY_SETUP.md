# Slack公開時のセキュリティ設定

## ✅ 実装済みセキュリティ対策

### 1. Slack Verification Token検証

Slack Events APIのリクエストを検証するように実装しました。

**設定方法:**
```powershell
# 環境変数に設定
$env:SLACK_VERIFICATION_TOKEN = "your_verification_token_from_slack"

# または設定ファイルから読み込み
```

**Slack App設定から取得:**
1. https://api.slack.com/apps にアクセス
2. あなたのSlack Appを選択
3. 「Basic Information」→「App Credentials」
4. 「Verification Token」をコピー

---

## 🔒 セキュリティ対策

### 現在の実装

1. **Verification Token検証**: ✅ 実装済み
   - Slackからのリクエストのみ受け付け
   - 不正なリクエストを拒否

2. **Botメッセージ無視**: ✅ 実装済み
   - Bot自身のメッセージは無視
   - 無限ループを防止

3. **ログ記録**: ✅ 実装済み
   - すべてのリクエストをログに記録
   - 異常なアクセスを検出可能

---

## ⚠️ 追加で推奨される対策

### 1. IPアドレス制限（オプション）

ngrok経由で公開する場合、特定のIPアドレスのみ許可：

```python
# slack_integration.pyに追加
ALLOWED_IPS = ["52.23.xxx.xxx"]  # SlackのIPアドレス範囲

@app.before_request
def limit_remote_addr():
    if request.remote_addr not in ALLOWED_IPS:
        return jsonify({"error": "Forbidden"}), 403
```

### 2. レート制限（オプション）

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/api/slack/events', methods=['POST'])
@limiter.limit("10 per minute")
def slack_events():
    # ...
```

### 3. HTTPS必須（ngrok経由）

ngrokの無料版でもHTTPSが使用されます：
- ✅ 自動的にHTTPS
- ✅ SSL/TLS暗号化

---

## 🎯 安全に公開する方法

### 方法1: ngrok経由（推奨）

**メリット:**
- ✅ HTTPS自動
- ✅ 一時的な公開（必要時のみ）
- ✅ 簡単に停止可能

**手順:**
```powershell
# 1. ngrokを起動
ngrok http 5114

# 2. 表示されたURLをSlack AppのEvent Subscriptionsに設定
# 例: https://xxxx-xxxx-xxxx.ngrok.io/api/slack/events

# 3. Verification Tokenを設定
$env:SLACK_VERIFICATION_TOKEN = "your_token"
```

### 方法2: Tailscale経由（最も安全）

**メリット:**
- ✅ VPN内のみアクセス可能
- ✅ 外部公開不要
- ✅ 最も安全

**手順:**
1. Tailscale経由でアクセス可能なURLを使用
2. Slack AppのEvent Subscriptionsに設定
3. 例: `http://100.93.120.33:5114/api/slack/events`

---

## 📊 セキュリティ比較

| 方法 | セキュリティ | 実装難易度 | 推奨度 |
|------|------------|-----------|--------|
| **ngrok + Verification Token** | ⭐⭐⭐⭐ | 簡単 | ✅ 推奨 |
| **Tailscale経由** | ⭐⭐⭐⭐⭐ | 簡単 | ✅ 最も安全 |
| **公開（認証なし）** | ⭐ | - | ❌ 非推奨 |

---

## ✅ 推奨設定

### 最小限のセキュリティ設定

1. **Verification Token設定**: ✅ 必須
   ```powershell
   $env:SLACK_VERIFICATION_TOKEN = "your_token"
   ```

2. **ngrok経由で公開**: ✅ 推奨
   - HTTPS自動
   - 一時的な公開

3. **ログ監視**: ✅ 推奨
   - 異常なアクセスを検出

---

## 🎉 結論

**Verification Tokenを設定すれば、ngrok経由で安全に公開できます。**

- ✅ Verification Token検証: 実装済み
- ✅ Botメッセージ無視: 実装済み
- ✅ ログ記録: 実装済み

**次のステップ:**
1. Slack AppからVerification Tokenを取得
2. 環境変数に設定
3. ngrokで公開

これで安全に公開できます！

