# 📥 n8nワークフローインポート手順（直接アクセス）

## 🎯 状況

Portal UI（http://localhost:5000）が起動していないため、**n8nに直接アクセス**してインポートします。

---

## ✅ 手順（2分）

### Step 1: n8nを開く

ブラウザで以下を開いてください（自動で開くはずです）:
```
http://localhost:5678
```

開かない場合は、手動でブラウザのアドレスバーに上記のURLを入力してください。

---

### Step 2: ログイン（必要に応じて）

n8nのログイン画面が表示された場合:
- 既存のアカウントでログイン
- または新規アカウント作成

---

### Step 3: ワークフローをインポート

1. **「Workflows」をクリック**（左メニュー）
2. **「Import from File」をクリック**（右上のボタン）
3. **ファイルを選択**:
   ```
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_workflows\browse_ai_manaos_integration.json
   ```
4. **インポート完了**

---

### Step 4: ワークフロー確認

インポート後、以下のワークフローが表示されるはずです:
- **名前**: "Browse AI → ManaOS統合"
- **ノード数**: 6個
- **状態**: 無効（後で有効化）

---

### Step 5: Webhook URL確認

1. **ワークフローを開く**（クリック）
2. **「Browse AI Webhook」ノードを確認**
3. **Webhook URLをコピー**:
   ```
   http://localhost:5678/webhook/browse-ai-webhook
   ```
   または、ノードをクリックして表示されるURL

---

## 🎯 次のステップ

インポート完了後:

1. **ワークフローを有効化**（トグルスイッチをON）
2. **Browse AIアカウント作成**（30分）
3. **Slack Webhook URL取得**（3分）
4. **Browse AI設定**（30分）
   - Webhook URL: `http://localhost:5678/webhook/browse-ai-webhook`
5. **テスト実行**（10分）

---

## 💡 トラブルシューティング

### n8nが開かない場合

1. **n8nが起動しているか確認**:
```powershell
Test-NetConnection -ComputerName localhost -Port 5678
```

2. **n8nを起動**（必要に応じて）:
```powershell
# Dockerの場合
docker start n8n

# ローカルインストールの場合
n8n start
```

### ワークフローファイルが見つからない場合

ファイルパスを確認:
```
C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_workflows\browse_ai_manaos_integration.json
```

---

## 📚 関連ファイル

- `browse_ai_manaos_integration.json` - ワークフローJSON
- `QUICK_START_BROWSE_AI.md` - クイックスタートガイド
- `IMPORT_INSTRUCTIONS.md` - インポート手順（詳細）

---

## 🎉 完了したら

インポートが完了したら、次のステップに進んでください！

**ManaOS、次の進化段階いこ**🔥



