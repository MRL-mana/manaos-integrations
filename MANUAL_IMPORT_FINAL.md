# 📥 ワークフローインポート（手動・最終手段）

## 🎯 状況

API経由の自動インポートが認証エラーのため失敗しました。
**手動インポートが最も確実**です。

---

## ✅ 手動インポート手順（2分）

### Step 1: n8nを開く

ブラウザで以下を開いてください:
```
http://localhost:5678
```

---

### Step 2: ワークフローをインポート

1. **「Workflows」をクリック**（左メニュー）
2. **「Import from File」をクリック**（右上のボタン、または「+」ボタンから）
3. **ファイルを選択**:
   ```
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_workflows\browse_ai_manaos_integration.json
   ```
4. **インポート完了**

---

### Step 3: ワークフロー確認

インポート後、以下が表示されます:
- **名前**: "Browse AI → ManaOS統合"
- **ノード数**: 6個
- **Webhook URL**: `http://localhost:5678/webhook/browse-ai-webhook`

---

### Step 4: ワークフローを有効化

1. **ワークフローを開く**（クリック）
2. **右上のトグルスイッチをON**にする
3. **保存**

---

## 🎯 次のステップ

インポート完了後:

1. ✅ **ワークフローを有効化**（完了）
2. **Browse AIアカウント作成**（30分）
3. **Slack Webhook URL取得**（3分）
4. **Browse AI設定**（30分）
   - Webhook URL: `http://localhost:5678/webhook/browse-ai-webhook`
5. **テスト実行**（10分）

---

## 💡 ヒント

- **ファイルパスをコピー**して、ファイル選択ダイアログに貼り付けられます
- **ドラッグ&ドロップ**でもインポートできます
- インポート後、**すぐに有効化**してください

---

## 📚 関連ファイル

- `QUICK_IMPORT_GUIDE.md` - クイックガイド
- `QUICK_START_BROWSE_AI.md` - Browse AI統合ガイド

---

**手動インポートは2分で完了します！**🔥



