# n8n 問題解決手順

## 現在の状況

✅ **完了:**
- n8nは起動中（http://localhost:5679）
- ワークフローはインポート済み（ID: 2ViGYzDtLBF6H4zn）

⏳ **残り作業:**
1. APIキーの取得・設定
2. ワークフローの再アクティベート（Webhook再登録）
3. 認証情報の設定（Google Drive、Slack）
4. 常時起動の設定

## ステップ1: APIキーの取得

### 手順

1. **ブラウザでn8nを開く**
   - http://localhost:5679 にアクセス
   - （既に開いている場合はそのまま使用）

2. **APIキーを作成**
   - 右上のユーザーアイコンをクリック
   - 「Settings」を選択
   - 左メニューから「API」を選択
   - 「Create API Key」をクリック
   - APIキー名を入力（例: `MCP Server`）
   - 「Create」をクリック
   - **生成されたAPIキーをコピー**（重要！）

3. **APIキーを設定**
   ```powershell
   $env:N8N_API_KEY = "コピーしたAPIキーをここに貼り付け"
   ```

4. **確認**
   ```powershell
   cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
   python n8n_mcp_server/check_workflow_status.py 2ViGYzDtLBF6H4zn
   ```

## ステップ2: ワークフローの再アクティベート

APIキーを設定したら、ワークフローを再アクティベートしてWebhookを再登録します。

### 方法1: Web UIから手動実行（推奨）

1. **ワークフローを開く**
   - n8nのWeb UIで「Workflows」をクリック
   - 「ManaOS Image Generation Workflow」を開く

2. **ワークフローを無効化→有効化**
   - 右上のトグルスイッチを一度OFFにする
   - 2-3秒待つ
   - 再度ONにする
   - これでWebhookが再登録されます

### 方法2: API経由で実行

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python n8n_mcp_server/reactivate_workflow.py 2ViGYzDtLBF6H4zn
```

## ステップ3: 認証情報の設定

### Google Drive認証

1. **ワークフローを開く**
   - 「ManaOS Image Generation Workflow」を開く

2. **Google Driveノードを開く**
   - Google Driveノードをクリック
   - 「Credential」セクションで「Create New Credential」をクリック
   - OAuth2認証を設定
   - 認証を完了

### Slack認証

1. **Slackノードを開く**
   - Slackノードをクリック
   - 「Credential」セクションで「Create New Credential」をクリック
   - OAuth2認証を設定
   - 認証を完了

## ステップ4: 常時起動の設定

### タスクスケジューラで設定（推奨）

1. **タスクスケジューラを開く**
   - Windowsキー → "タスクスケジューラ" を検索

2. **基本タスクの作成**
   - 「基本タスクの作成」をクリック
   - 名前: `n8n Auto Start`
   - トリガー: 「ログオン時」
   - 操作: 「プログラムの開始」
   - プログラム: `n8n`
   - 引数: `start --port 5679`
   - 開始場所: `%USERPROFILE%\.n8n`

詳細は `n8n_常時起動_簡単手順.md` を参照してください。

## ステップ5: テスト実行

すべての設定が完了したら、ワークフローをテスト実行します。

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python n8n_mcp_server/execute_workflow.py 2ViGYzDtLBF6H4zn
```

## トラブルシューティング

### APIキーが無効な場合

- ローカルのn8nから新しいAPIキーを作成してください
- このはサーバーのn8nのAPIキーは使用できません

### Webhookが404エラーの場合

- ワークフローを一度無効化→有効化してください
- WebhookノードのPathが `comfyui-generated` になっているか確認してください

### 認証情報が設定できない場合

- n8nのWeb UIから直接設定してください
- 各サービスのOAuth2認証が必要です











