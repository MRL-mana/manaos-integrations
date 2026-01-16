# n8n設定完了レポート

## 完了した作業

### 1. n8nのインストール・起動
- ✅ 母艦（新PC）でn8nをインストール
- ✅ ポート5679で起動（ポート5678は使用中だったため）
- ✅ ブラウザで `http://localhost:5679` にアクセス可能

### 2. APIキーの取得・設定
- ✅ n8nのWeb UIからAPIキーを取得
- ✅ MCP設定ファイル（`~/.cursor/mcp.json`）に設定
- ✅ Base URLを `http://localhost:5679` に更新
- ✅ API接続確認成功（Status: 200）

### 3. ワークフローのインポート
- ✅ ワークフローテンプレートを簡略化（Obsidianノードを削除）
- ✅ n8nにワークフローをインポート成功
- ✅ ワークフローを有効化成功
- ✅ ワークフローID: `2ViGYzDtLBF6H4zn`

## ワークフロー構成

### インポートされたワークフロー
- **名前**: ManaOS Image Generation Workflow
- **ID**: `2ViGYzDtLBF6H4zn`
- **URL**: http://localhost:5679/workflow/2ViGYzDtLBF6H4zn

### ワークフローのノード
1. **Webhook** (`n8n-nodes-base.webhook`)
   - パス: `comfyui-generated`
   - メソッド: POST
   - Webhook URL: `http://localhost:5679/webhook/comfyui-generated`

2. **Google Drive Upload** (`n8n-nodes-base.googleDrive`)
   - 操作: upload
   - ファイル名: `={{ $json.prompt_id }}.png`

3. **Slack Notify** (`n8n-nodes-base.slack`)
   - チャンネル: `#manaos-notifications`
   - メッセージ: 画像生成完了通知

4. **Webhook Response** (`n8n-nodes-base.respondToWebhook`)
   - レスポンス: JSON形式

## 次のステップ

### 1. 統合APIサーバーにWebhook URLを設定

`unified_api_server.py` の環境変数に以下を設定：

```bash
N8N_WEBHOOK_URL=http://localhost:5679/webhook/comfyui-generated
```

または、`.env` ファイルに追加：

```env
N8N_WEBHOOK_URL=http://localhost:5679/webhook/comfyui-generated
```

### 2. 認証情報の設定

n8nのWeb UIで以下の認証情報を設定：

1. **Google Drive**
   - Settings → Credentials → Google Drive API
   - OAuth2認証を設定

2. **Slack**
   - Settings → Credentials → Slack API
   - OAuth2認証を設定

### 3. ワークフローのテスト

統合APIサーバーからComfyUIで画像生成した際に、自動的にn8nワークフローが実行されるか確認：

```bash
# 統合APIサーバーを起動
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python unified_api_server.py

# 別のターミナルで画像生成をテスト
curl -X POST http://localhost:9500/api/comfyui/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test image", "width": 512, "height": 512}'
```

## 設定ファイル

### MCP設定 (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "n8n": {
      "command": "python",
      "args": ["-m", "n8n_mcp_server.server"],
      "env": {
        "N8N_BASE_URL": "http://localhost:5679",
        "N8N_API_KEY": "your_n8n_api_key_here"
      },
      "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
    }
  }
}
```

## トラブルシューティング

### n8nが起動しない
```powershell
# プロセスを確認
Get-Process -Name node | Where-Object { $_.Path -like "*n8n*" }

# ポートを確認
Get-NetTCPConnection -LocalPort 5679

# 再起動
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_n8n_local.ps1
```

### APIキーが無効
1. n8nのWeb UIで新しいAPIキーを作成
2. `set_api_key_manual.ps1` で再設定
3. Cursorを再起動

### ワークフローが実行されない
1. n8nのWeb UIでワークフローが有効になっているか確認
2. Webhook URLが正しいか確認
3. 統合APIサーバーのログを確認

## 完了状況

- ✅ n8nのインストール・起動
- ✅ APIキーの取得・設定
- ✅ ワークフローのインポート・有効化
- ⏳ 統合APIサーバーへのWebhook URL設定
- ⏳ 認証情報の設定（Google Drive、Slack）
- ⏳ ワークフローのテスト















