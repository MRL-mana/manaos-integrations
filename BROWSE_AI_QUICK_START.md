# 🚀 Browse AIロボット作成クイックスタート

## 🎯 5分でロボットを作成

### Step 1: Browse AIにアクセス

1. **https://www.browse.ai/ にアクセス**
2. **ログイン**（アカウントがない場合はサインアップ）

---

### Step 2: ロボットを作成

1. **ダッシュボードで「Create Robot」をクリック**
2. **「Monitor a Website」を選択**
3. **URLを入力**:
   ```
   https://example.com/products
   ```
   （監視したいWebサイトのURL）
4. **ロボット名を入力**:
   ```
   Sale Monitor
   ```
5. **「Create」または「Next」をクリック**

---

### Step 3: データ抽出を設定

1. **ページが読み込まれるまで待つ**
2. **抽出したい要素をクリック**:
   - 商品名をクリック
   - 価格をクリック
   - 割引率をクリック
3. **Browse AIが自動的に要素を認識**
4. **「Save」または「Next」をクリック**

---

### Step 4: Webhookを設定

1. **「Integrations」タブを開く**
2. **「Add Webhook」をクリック**
3. **Webhook URLを入力**:
   ```
   https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
   ```
   （ngrokのURLを使用）
4. **「Save」をクリック**

---

### Step 5: テスト実行

1. **「Run」または「Test」ボタンをクリック**
2. **データが抽出されるか確認**
3. **n8nのワークフローでデータを受信**
4. **Slack通知が届くか確認**

---

## 💡 ヒント

### ロボット名の付け方

- **Sale Monitor** - セール監視
- **Trending Monitor** - トレンド監視
- **Competitor Monitor** - 競合監視
- **Price Tracker** - 価格追跡
- **Stock Monitor** - 在庫監視

---

### 監視するURLの例

- **ECサイト**: `https://example.com/products`
- **GitHubトレンド**: `https://github.com/trending`
- **技術ニュース**: `https://techcrunch.com`
- **競合サイト**: `https://competitor.com/products`

---

## 🆘 困ったときは

### Browse AIのドキュメント

- **公式ドキュメント**: https://docs.browse.ai/
- **サポート**: https://www.browse.ai/support

---

### よくある質問

**Q: 要素が選択できない**
A: ページが完全に読み込まれるまで待ってください。

**Q: データが正しく抽出されない**
A: 要素の選択を再確認して、必要に応じて調整してください。

**Q: Webhookが動作しない**
A: ngrokが起動しているか、Webhook URLが正しいか確認してください。

---

**ロボット作成で困ったら、Browse AIのドキュメントを確認してください！**🔥


