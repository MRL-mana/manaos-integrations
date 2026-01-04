# 🔧 Slack URLエラー修正

## 🎯 問題

エラー: `無効な URL: URLは「http」または「https」で始まる必要があります。`

**URL**: `https://hooks.slack.com/services/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`

URLは正しく`https://`で始まっているのにエラーが出ています。

---

## ✅ 解決方法

### Step 1: URLフィールドを「Fixed」モードに切り替え

1. **Slack通知ノードをクリック**
2. **URLフィールドの右側を確認**
3. **「Expression」が選択されている場合、クリックして「Fixed」に切り替え**

---

### Step 2: URLを直接入力

1. **URLフィールドをクリック**
2. **既存の内容をすべて削除**
3. **以下をコピー&ペースト**:
   ```
   https://hooks.slack.com/services/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
   ```
4. **Enterキーを押すか、フィールド外をクリック**

---

### Step 3: 設定確認

**確認事項**:
- ✅ **URL**: `https://hooks.slack.com/services/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`（Fixedモード）
- ✅ **Method**: POST
- ✅ **Send Body**: ON
- ✅ **Body Content Type**: JSON
- ✅ **Specify Body**: Using JSON
- ✅ **JSON Body**: `{{ { "text": $json.message } }}`

---

### Step 4: 保存してテスト

1. **「Save」をクリック**
2. **右上の「Execute step」ボタンをクリック**
3. **エラーが解消されたか確認**

---

## 💡 よくある問題

### 問題1: Expressionモードになっている

**解決策**: URLフィールドを「Fixed」モードに切り替え

---

### 問題2: URLに余分な文字が含まれている

**解決策**: URLフィールドをクリアして、再度入力

---

### 問題3: URLが途中で切れている

**解決策**: 完全なURLをコピー&ペースト

**完全なURL**:
```
https://hooks.slack.com/services/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
```

---

## 🧪 テスト手順

### Step 1: URLを修正

1. **URLフィールドを「Fixed」モードに切り替え**
2. **完全なURLを入力**

### Step 2: 保存

1. **「Save」をクリック**

### Step 3: テスト実行

1. **右上の「Execute step」ボタンをクリック**
2. **エラーが解消されたか確認**
3. **Slack通知が届くか確認**

---

## 📚 関連ファイル

- `SLACK_WEBHOOK_URL.md` - Slack Webhook URL設定ガイド
- `FIX_SLACK_URL_NOW.md` - URL設定修正ガイド

---

**URLフィールドを「Fixed」モードに切り替えて、完全なURLを入力してください！**🔥


