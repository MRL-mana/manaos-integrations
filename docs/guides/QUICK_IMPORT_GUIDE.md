# ⚡ クイックインポートガイド（n8n直接アクセス）

## 🎯 状況

Portal UI（http://localhost:5000）が起動していないため、**n8nに直接アクセス**します。

---

## ✅ 手順（2分）

### 1. n8nを開く

ブラウザで以下を開いてください:
```
http://localhost:5678
```

**自動で開くはずです**（実行済み）

---

### 2. ワークフローをインポート

1. **「Workflows」をクリック**（左メニュー）
2. **「Import from File」をクリック**（右上のボタン）
3. **ファイルを選択**:
   ```
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_workflows\browse_ai_manaos_integration.json
   ```
4. **インポート完了**

---

### 3. ワークフロー確認

インポート後、以下が表示されます:
- **名前**: "Browse AI → ManaOS統合"
- **ノード数**: 6個

---

### 4. Webhook URL確認

ワークフローを開いて、「Browse AI Webhook」ノードのURLを確認:
```
http://localhost:5678/webhook/browse-ai-webhook
```

---

## 🎯 次のステップ

1. **ワークフローを有効化**（トグルスイッチをON）
2. **Browse AIアカウント作成**（30分）
3. **Slack Webhook URL取得**（3分）
4. **Browse AI設定**（30分）
5. **テスト実行**（10分）

---

## 📚 詳細

- `IMPORT_WORKFLOW_DIRECT.md` - 詳細手順
- `QUICK_START_BROWSE_AI.md` - クイックスタートガイド

---

**n8nを開いて、インポートしてください！**🔥



