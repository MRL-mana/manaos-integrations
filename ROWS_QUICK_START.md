# Rows統合 クイックスタートガイド

## 5分で始めるRows統合

### 1. 環境変数の設定

```bash
# .envファイルまたは環境変数に設定
export ROWS_API_KEY="your_rows_api_key_here"
export ROWS_WEBHOOK_URL="http://localhost:9500/api/rows/webhook"
export N8N_WEBHOOK_URL="http://localhost:5678/webhook/rows-manaos-integration"  # オプション
```

### 2. 統合APIサーバーの起動

```bash
cd manaos_integrations
python unified_api_server.py
```

サーバーが起動すると、Rows統合が自動的に初期化されます。

### 3. 動作確認

```bash
# テストスクリプトを実行
python test_rows_integration.py
```

## よく使う操作

### スプレッドシートを作成

```python
import requests

response = requests.post("http://localhost:9500/api/rows/spreadsheets", json={
    "title": "テストスプレッドシート",
    "description": "テスト用"
})

spreadsheet_id = response.json()["spreadsheet"]["id"]
print(f"作成完了: {spreadsheet_id}")
```

### データを送信

```python
response = requests.post("http://localhost:9500/api/rows/data/send", json={
    "spreadsheet_id": spreadsheet_id,
    "data": [
        {"日付": "2025-01-28", "売上": 100000, "利益": 30000},
        {"日付": "2025-01-29", "売上": 120000, "利益": 36000}
    ],
    "sheet_name": "Sheet1",
    "append": True
})
```

### AIで分析

```python
response = requests.post("http://localhost:9500/api/rows/ai/query", json={
    "spreadsheet_id": spreadsheet_id,
    "query": "この売上データ、傾向分析してグラフ出して"
})

print(response.json()["result"])
```

## 実用例スクリプト

### 売上分析
```bash
python rows_example_sales_analysis.py
```

### ログ管理
```bash
python rows_example_log_management.py
```

### 収益管理
```bash
python rows_example_revenue_management.py
```

## 利用可能なAPIエンドポイント

### 基本操作
- `GET /api/rows/spreadsheets` - 一覧取得
- `POST /api/rows/spreadsheets` - 作成
- `GET /api/rows/spreadsheets/<id>` - 取得

### AI機能
- `POST /api/rows/ai/query` - 自然言語クエリ
- `POST /api/rows/ai/analyze` - データ分析

### データ操作
- `POST /api/rows/data/send` - データ送信
- `POST /api/rows/batch/update` - バッチ更新
- `POST /api/rows/import/csv` - CSVインポート
- `POST /api/rows/export/csv` - CSVエクスポート

### 高度な機能
- `POST /api/rows/sync/auto` - 自動同期
- `POST /api/rows/dashboard/create` - ダッシュボード作成
- `POST /api/rows/export/slack` - Slack送信
- `POST /api/rows/webhook` - Webhook受信

## トラブルシューティング

### Rows APIが利用できない

```bash
# 環境変数を確認
echo $ROWS_API_KEY

# 統合APIサーバーのログを確認
tail -f logs/unified_api_server.log
```

### サーバーに接続できない

```bash
# サーバーが起動しているか確認
curl http://localhost:9500/health

# サーバーを起動
python unified_api_server.py
```

## 次のステップ

1. [詳細ドキュメント](./ROWS_INTEGRATION.md)を読む
2. [機能一覧](./ROWS_FEATURES_SUMMARY.md)を確認
3. 実用例スクリプトを実行してみる
4. n8nワークフローを設定する












