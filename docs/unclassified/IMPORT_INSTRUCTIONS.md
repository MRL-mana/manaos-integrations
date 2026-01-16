# 📥 n8nワークフローインポート手順

## 🔄 自動インポート（試行済み）

自動インポートを試みましたが、n8nのAPI認証が必要なため失敗しました。

---

## ✅ 手動インポート方法（推奨）

### 方法A: Portal UI経由（最も簡単）

1. **ブラウザで開く**: http://localhost:5000
2. **「⚙️ 自動化ワークフロー（n8n）」セクションを開く**
3. **「ワークフローをインポート」をクリック**
4. **ファイルを選択**: 
   ```
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_workflows\browse_ai_manaos_integration.json
   ```
5. **インポート完了**

---

### 方法B: n8n直接アクセス

1. **ブラウザで開く**: http://localhost:5678
2. **ログイン**（必要に応じて）
3. **「Workflows」をクリック**
4. **「Import from File」をクリック**
5. **ファイルを選択**: 
   ```
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_workflows\browse_ai_manaos_integration.json
   ```
6. **インポート完了**

---

### 方法C: Pythonスクリプト経由（APIキーが必要）

1. **n8n APIキーを取得**:
   - n8n UI → Settings → API
   - APIキーを生成

2. **環境変数設定**:
```powershell
$env:N8N_API_KEY = "your-api-key"
```

3. **スクリプト実行**:
```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python import_n8n_workflow.py
```

---

## ✅ インポート後の確認

1. **ワークフローが表示されているか確認**
2. **ワークフロー名**: "Browse AI → ManaOS統合"
3. **ノード数**: 6個
4. **Webhook URL確認**: 
   ```
   http://localhost:5678/webhook/browse-ai-webhook
   ```

---

## 🎯 次のステップ

インポート完了後:

1. **ワークフローを有効化**（n8n UIで）
2. **Browse AIアカウント作成**（30分）
3. **Slack Webhook URL取得**（3分）
4. **Browse AI設定**（30分）
5. **テスト実行**（10分）

---

## 📚 関連ファイル

- `import_n8n_workflow.py` - Pythonインポートスクリプト
- `n8n_workflows/browse_ai_manaos_integration.json` - ワークフローJSON
- `QUICK_START_BROWSE_AI.md` - クイックスタートガイド



