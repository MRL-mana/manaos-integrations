# Excel/LLM処理 n8n統合ガイド

## 概要

Excel/LLM処理をn8nワークフローと統合して、自動化ワークフローを構築できます。

## n8nワークフローのインポート

### 1. n8nワークフローのインポート

1. n8nを開く: http://localhost:5678
2. 「Workflows」→「Import from File」
3. `n8n_workflows/excel_llm_integration_workflow.json` を選択
4. ワークフローをインポート

### 2. 設定

#### Webhookトリガーの設定

1. 「Webhookトリガー」ノードを選択
2. 「Listen for Test Event」をクリック
3. Webhook URLをコピー（例: `http://localhost:5678/webhook/excel-llm-process`）

#### Slack通知の設定

1. 「Slack通知」ノードを選択
2. Slack API認証情報を設定
3. チャンネル名を設定（デフォルト: `#manaos-notifications`）

#### Obsidian記録の設定

1. 「Obsidian記録」ノードを選択
2. Obsidian Vaultパスを設定

### 3. ワークフローの実行

#### Webhook経由で実行

```bash
curl -X POST http://localhost:5678/webhook/excel-llm-process \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "C:\\path\\to\\data.xlsx",
    "task": "異常値検出"
  }'
```

#### Pythonから実行

```python
import requests

response = requests.post(
    "http://localhost:5678/webhook/excel-llm-process",
    json={
        "file_path": "C:\\path\\to\\data.xlsx",
        "task": "異常値検出"
    }
)

result = response.json()
print(result)
```

## ワークフロー構成

1. **Webhookトリガー** - n8nワークフローをトリガー
2. **ManaOS Excel/LLM処理** - Excel/CSVファイルをLLMで処理
3. **成功判定** - 処理結果を判定
4. **Slack通知** - 成功時にSlackに通知
5. **Obsidian記録** - 成功時にObsidianに記録
6. **Webhook応答** - 結果を返す
7. **エラー応答** - エラー時にエラーを返す

## 使用例

### 1. 定期実行ワークフロー

n8nの「Schedule Trigger」ノードを追加して、定期的にExcel分析を実行できます。

```json
{
  "parameters": {
    "rule": {
      "interval": [
        {
          "field": "hours",
          "hoursInterval": 1
        }
      ]
    }
  },
  "name": "1時間ごとに実行",
  "type": "n8n-nodes-base.scheduleTrigger",
  "typeVersion": 1,
  "position": [50, 300]
}
```

### 2. ファイル監視ワークフロー

「File System Trigger」ノードを追加して、ファイルが追加されたときに自動実行できます。

```json
{
  "parameters": {
    "path": "/path/to/excel/files",
    "event": "fileAdded"
  },
  "name": "ファイル監視",
  "type": "n8n-nodes-base.fileSystemTrigger",
  "typeVersion": 1,
  "position": [50, 300]
}
```

### 3. Slackコマンド経由の実行

「Slack Trigger」ノードを追加して、Slackコマンドから実行できます。

```json
{
  "parameters": {
    "event": "command",
    "command": "/excel-analyze"
  },
  "name": "Slackコマンド",
  "type": "n8n-nodes-base.slackTrigger",
  "typeVersion": 1,
  "position": [50, 300]
}
```

## カスタマイズ

### タスクの追加

`task`パラメータに独自のタスクを追加できます：

- `異常値検出` - 異常値や外れ値を検出
- `集計分析` - データの集計と分析
- `ミス検出` - データのミスや誤りを検出
- `傾向分析` - データの傾向やパターンを分析
- `カスタムタスク` - 独自のタスクを指定

### 通知先の変更

Slack通知のチャンネルやObsidianの保存先を変更できます。

### エラーハンドリングの追加

エラー時に別の処理を実行するノードを追加できます。

## トラブルシューティング

### Webhookが応答しない

- n8nが起動しているか確認
- Webhook URLが正しいか確認
- n8nのログを確認

### ManaOS APIに接続できない

- 統合APIサーバーが起動しているか確認: `curl http://localhost:9500/health`
- Excel/LLM統合が有効か確認: `curl http://localhost:9500/api/integrations/status`

### Slack通知が送信されない

- Slack API認証情報が正しいか確認
- チャンネル名が正しいか確認
- Slack APIの権限を確認

## 次のステップ

1. **複数ファイルの一括処理**
   - 複数のExcelファイルを一括で処理

2. **条件分岐の追加**
   - 分析結果に応じて処理を分岐

3. **データベースへの保存**
   - 分析結果をデータベースに保存

4. **レポート生成**
   - 分析結果からレポートを自動生成
