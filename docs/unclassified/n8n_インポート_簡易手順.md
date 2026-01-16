# n8nワークフロー インポート 簡易手順

**現在の状況:** n8nのAPI経由でのインポートには認証が必要です。

---

## ✅ 最も簡単な方法: ブラウザで手動インポート（2分）

### ステップ1: n8nにアクセス

ブラウザで以下を開く（既に開いている場合はスキップ）:
```
http://100.93.120.33:5678
```

### ステップ2: ワークフローをインポート

1. **「Workflows」をクリック**（左サイドバー）
2. **「Import from File」をクリック**（右上のボタン）
3. **ファイルを選択**
   ```
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_workflow_template.json
   ```
4. **「Import」をクリック**

### ステップ3: ワークフローを有効化

1. **インポートしたワークフローを開く**（「ManaOS Image Generation Workflow」をクリック）
2. **右上の「Active」スイッチをONにする**
3. **「Save」をクリック**

---

## 🎯 インポート後の確認

### 1. Webhook URLを確認

ワークフローを開いて、「Webhook」ノードを確認：
- Webhook URL: `http://100.93.120.33:5678/webhook/comfyui-generated`

### 2. 環境変数を設定

```powershell
$env:N8N_WEBHOOK_URL = "http://100.93.120.33:5678/webhook/comfyui-generated"
```

### 3. 統合APIサーバーを再起動（環境変数を反映）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python unified_api_server.py
```

---

## 📊 進捗状況

**現在:** 98%完了  
**残り:** 2%（n8nワークフローのインポートのみ）

**所要時間:** 約2分

---

## 💡 100%完了後の状態

**「生成 → 保存 → Obsidian記録 → Slack通知」が1本通る完全自動化ループ**

すべてが自動で動作する状態になります。

---

**次のアクション:** ブラウザでn8nワークフローをインポートするだけ！


















