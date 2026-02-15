# Rows統合ガイド

## 概要

Rowsは「Excel × Notion × ChatGPT」のようなAIスプレッドシートツールです。ManaOSとの統合により、以下の機能が利用できます：

- **自然言語でのデータ操作**: 「この売上データ、傾向分析してグラフ出して」などの日本語指示で即実行
- **AI関数生成**: Excel地獄から解放、AIが関数を自動生成
- **強力なAPI/Webhook連携**: n8n・ManaOSと相性抜群
- **データ分析・ログ管理・収益管理**: 業務効率化に最適

## 特徴

### できること

1. **日本語での自然な操作**
   - 「この売上データ、傾向分析してグラフ出して」
   - 「この表を要約してSlackに投げて」
   - → 即実行

2. **AIが関数を書いてくれる**
   - Excel地獄から解放
   - 複雑な計算式も自然言語で指示

3. **API / Webhook / 外部サービス連携が超強い**
   - n8n・ManaOSと相性◎
   - 自動化ワークフローが簡単に構築可能

4. **データ分析・ログ管理・収益管理向き**
   - 「考える人」向け（マナタイプ）

## セットアップ

### 1. Rows APIキーの取得

1. [Rows公式サイト](https://rows.com)にアクセス
2. アカウントを作成/ログイン
3. 設定画面からAPIキーを取得

### 2. 環境変数の設定

`.env`ファイルまたは環境変数に以下を設定：

```bash
# Rows API設定
ROWS_API_KEY=your_rows_api_key_here
ROWS_WEBHOOK_URL=http://127.0.0.1:9510/api/rows/webhook

# n8n連携（オプション）
N8N_WEBHOOK_URL=http://127.0.0.1:5678/webhook/rows-manaos-integration
```

### 3. 統合APIサーバーの起動

```bash
cd manaos_integrations
python unified_api_server.py
```

サーバーが起動すると、Rows統合が自動的に初期化されます。

## APIエンドポイント

### スプレッドシート操作

#### スプレッドシート一覧を取得
```http
GET /api/rows/spreadsheets?limit=50
```

#### スプレッドシートを作成
```http
POST /api/rows/spreadsheets
Content-Type: application/json

{
  "title": "売上管理",
  "description": "月次売上データ"
}
```

#### スプレッドシート情報を取得
```http
GET /api/rows/spreadsheets/{spreadsheet_id}
```

### AI機能

#### 自然言語でクエリ実行
```http
POST /api/rows/ai/query
Content-Type: application/json

{
  "spreadsheet_id": "sp_xxxxx",
  "query": "この売上データ、傾向分析してグラフ出して",
  "context": {
    "range": "A1:Z100"
  }
}
```

#### データ分析を実行
```http
POST /api/rows/ai/analyze
Content-Type: application/json

{
  "spreadsheet_id": "sp_xxxxx",
  "analysis_type": "trend",
  "target_range": "A1:Z100"
}
```

### データ送信

#### ManaOSからRowsにデータを送信
```http
POST /api/rows/data/send
Content-Type: application/json

{
  "spreadsheet_id": "sp_xxxxx",
  "data": {
    "日付": "2025-01-28",
    "売上": 100000,
    "利益": 30000
  },
  "sheet_name": "Sheet1",
  "append": true
}
```

### 外部サービス連携

#### Slackに要約を送信
```http
POST /api/rows/export/slack
Content-Type: application/json

{
  "spreadsheet_id": "sp_xxxxx",
  "sheet_name": "Sheet1",
  "range": "A1:Z100",
  "channel": "#manaos-notifications"
}
```

## 使用例

### 例1: 売上データの傾向分析

```python
import requests

# 1. スプレッドシートを作成
response = requests.post("http://127.0.0.1:9510/api/rows/spreadsheets", json={
    "title": "売上分析",
    "description": "月次売上データの分析"
})
spreadsheet_id = response.json()["spreadsheet"]["id"]

# 2. データを送信
requests.post("http://127.0.0.1:9510/api/rows/data/send", json={
    "spreadsheet_id": spreadsheet_id,
    "data": [
        {"月": "2024-01", "売上": 1000000, "利益": 300000},
        {"月": "2024-02", "売上": 1200000, "利益": 360000},
        {"月": "2024-03", "売上": 1500000, "利益": 450000}
    ]
})

# 3. AIで傾向分析
response = requests.post("http://127.0.0.1:9510/api/rows/ai/query", json={
    "spreadsheet_id": spreadsheet_id,
    "query": "この売上データ、傾向分析してグラフ出して"
})
print(response.json()["result"])
```

### 例2: 表を要約してSlackに送信

```python
import requests

# スプレッドシートのデータを要約してSlackに送信
response = requests.post("http://127.0.0.1:9510/api/rows/export/slack", json={
    "spreadsheet_id": "sp_xxxxx",
    "sheet_name": "Sheet1",
    "channel": "#manaos-notifications"
})
```

### 例3: n8nワークフローとの連携

1. `n8n_workflows/rows_integration_workflow.json`をn8nにインポート
2. Rows API認証情報を設定
3. Webhook URLを設定: `http://127.0.0.1:5678/webhook/rows-manaos-integration`

Rowsでデータが更新されると、自動的に：
- ManaOS APIに通知
- AI分析を実行
- Slackに通知
- Obsidianに記録

## n8nワークフロー

### インポート方法

```bash
# n8nワークフローをインポート
curl -X POST http://127.0.0.1:5678/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d @manaos_integrations/n8n_workflows/rows_integration_workflow.json
```

### ワークフロー構成

1. **Rows Webhook**: Rowsからのイベントを受信
2. **ManaOS API**: 統合APIサーバーに通知
3. **Rows AI分析**: AIでデータ分析を実行
4. **Slack通知**: 結果をSlackに送信
5. **Obsidian記録**: 分析結果をObsidianに記録

## トラブルシューティング

### Rows APIが利用できない

```bash
# 環境変数を確認
echo $ROWS_API_KEY

# 統合APIサーバーのログを確認
tail -f logs/unified_api_server.log
```

### Webhookが受信できない

1. ファイアウォール設定を確認
2. `ROWS_WEBHOOK_URL`が正しく設定されているか確認
3. n8nのWebhook URLが正しいか確認

### AIクエリが失敗する

- スプレッドシートIDが正しいか確認
- データが存在するか確認
- APIキーの権限を確認

## 参考リンク

- [Rows公式サイト](https://rows.com)
- [Rows APIドキュメント](https://docs.rows.com)
- [ManaOS統合APIドキュメント](./API_SPEC.md)

## 高度な機能

### バッチ処理

複数のセルを一括更新：

```http
POST /api/rows/batch/update
Content-Type: application/json

{
  "spreadsheet_id": "sp_xxxxx",
  "updates": [
    {"cell": "A1", "value": "値1"},
    {"cell": "B1", "value": "値2"},
    {"cell": "C1", "value": "値3"}
  ],
  "sheet_name": "Sheet1"
}
```

### CSVインポート/エクスポート

```http
# CSVインポート
POST /api/rows/import/csv
Content-Type: application/json

{
  "spreadsheet_id": "sp_xxxxx",
  "csv_file_path": "/path/to/data.csv",
  "sheet_name": "Sheet1",
  "has_header": true
}

# CSVエクスポート
POST /api/rows/export/csv
Content-Type: application/json

{
  "spreadsheet_id": "sp_xxxxx",
  "sheet_name": "Sheet1",
  "range": "A1:Z100",
  "output_path": "/path/to/output.csv"
}
```

### 自動同期

データの自動同期機能：

```http
POST /api/rows/sync/auto
Content-Type: application/json

{
  "spreadsheet_id": "sp_xxxxx",
  "source_data": [
    {"id": "1", "name": "項目1", "value": 100},
    {"id": "2", "name": "項目2", "value": 200}
  ],
  "key_column": "id",
  "sheet_name": "Sheet1"
}
```

### ダッシュボード作成

AIでダッシュボードを自動生成：

```http
POST /api/rows/dashboard/create
Content-Type: application/json

{
  "spreadsheet_id": "sp_xxxxx",
  "dashboard_config": {
    "description": "売上分析ダッシュボード",
    "metrics": ["売上", "利益", "利益率"],
    "charts": ["売上推移", "利益率グラフ"]
  },
  "sheet_name": "Dashboard"
}
```

## テストとクイックスタート

### クイックスタート

```bash
# クイックスタートスクリプトを実行
python rows_quick_start.py
```

### テスト実行

```bash
# 全機能のテスト
python test_rows_integration.py

# 実用例（売上分析）
python rows_example_sales_analysis.py
```

## エラーハンドリング

Rows統合には以下のエラーハンドリング機能が実装されています：

- **自動リトライ**: ネットワークエラーやタイムアウト時に自動リトライ（最大3回）
- **レート制限対応**: 429エラー時にRetry-Afterヘッダーを確認して適切に待機
- **詳細なエラーログ**: エラーの種類と原因を詳細に記録
- **認証エラー検出**: 401エラー時にAPIキーの確認を促す

## まとめ

Rows統合により、以下のことが可能になります：

✅ 日本語で自然にデータ操作  
✅ AIが関数を自動生成  
✅ n8n/ManaOSとの強力な連携  
✅ データ分析・ログ管理・収益管理の自動化  
✅ バッチ処理・CSVインポート/エクスポート  
✅ 自動同期・ダッシュボード自動生成  
✅ 堅牢なエラーハンドリングとリトライ機能  

「Excelに戻れなくなる」「Notionの表より100倍"計算向き"」「考える人向け（マナタイプ）」













