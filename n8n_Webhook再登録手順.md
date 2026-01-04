# n8n Webhook再登録手順

## 現在の状況

- ✅ ワークフローは有効（active: はい）
- ❌ Webhookが404エラーで登録されていない

## 解決方法

n8nのWeb UIで手動でワークフローを再アクティベートしてください。

### 手順

1. **ワークフローを開く**
   - ブラウザで http://localhost:5679/workflow/2ViGYzDtLBF6H4zn を開く
   - （既に開いている場合はそのまま使用）

2. **ワークフローを無効化→有効化**
   - ワークフローエディタの右上にあるトグルスイッチを確認
   - 現在「ON」（緑色）になっている場合は、一度「OFF」に切り替え
   - **5秒以上待つ**（重要！）
   - 再度「ON」に切り替え
   - これでWebhookが再登録されます

3. **確認**
   - Webhookノード（最初のノード）をクリック
   - 「Path」が `comfyui-generated` になっていることを確認
   - ワークフローが有効（緑のチェックマーク）になっていることを確認

4. **テスト実行**
   ```powershell
   cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
   python -c "import os; os.environ['N8N_API_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxZTMzZjMzOS1jNjRhLTQ3ZTUtYjI2OC0wMDhiYWZlNmVkYjAiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2OTYzNzM0fQ.tKZWwjMxBjqfUC47mlh2u7YD7PylAh80dbohYTphEhE'; import subprocess; subprocess.run(['python', 'n8n_mcp_server/execute_workflow.py', '2ViGYzDtLBF6H4zn'])"
   ```

## 注意事項

- **無効化→有効化の間は5秒以上待つ**ことが重要です
- Webhookの再登録には数秒かかることがあります
- ワークフローが有効になっていても、Webhookが登録されていない場合があります

## トラブルシューティング

### まだ404エラーが出る場合

1. n8nを再起動してみる
2. ワークフローを保存してから再度無効化→有効化
3. Webhookノードの設定を確認（Pathが正しいか）











