# Excel/LLM処理統合 - ManaOS統合ドキュメント

## 概要

Excel/CSVファイルをLLMで処理する機能をManaOSに統合しました。
VisiDataとOllamaを組み合わせて、「入れた瞬間から元取れる」コスパ最強のExcel分析機能を提供します。

## セットアップ

### Windows（PowerShell）

```powershell
# 一括セットアップ
.\setup_visidata_ollama_complete.ps1
```

### Linux（Bash）

```bash
# 一括セットアップ
./setup_visidata_ollama_complete.sh
```

## APIエンドポイント

### 1. Excel/CSVファイルをLLMで処理

**エンドポイント:** `POST /api/excel/process`

**リクエスト:**
```json
{
    "file_path": "data.xlsx",
    "task": "異常値検出"
}
```

**レスポンス:**
```json
{
    "success": true,
    "response": "LLM分析結果...",
    "model": "qwen2.5:7b",
    "output_file": "data_llm_analysis.txt",
    "rows": 100,
    "columns": 5
}
```

**タスク例:**
- `異常値検出` - 異常値や外れ値を検出
- `集計分析` - データの集計と分析
- `ミス検出` - データのミスや誤りを検出
- `傾向分析` - データの傾向やパターンを分析

### 2. Excel/CSVファイルの要約を取得（LLM不使用）

**エンドポイント:** `POST /api/excel/summary`

**リクエスト:**
```json
{
    "file_path": "data.xlsx"
}
```

**レスポンス:**
```json
{
    "success": true,
    "summary": "データ概要:\n- 行数: 100\n- 列数: 5\n...",
    "rows": 100,
    "columns": 5,
    "column_names": ["列1", "列2", "列3", "列4", "列5"]
}
```

## 使用例

### Pythonから使用

```python
import requests

# Excel/CSVファイルをLLMで処理
response = requests.post(
    "http://localhost:9500/api/excel/process",
    json={
        "file_path": "data.xlsx",
        "task": "異常値検出"
    }
)

result = response.json()
if result["success"]:
    print(f"分析完了: {result['output_file']}")
    print(result["response"])
```

### curlから使用

```bash
# Excel/CSVファイルをLLMで処理
curl -X POST http://localhost:9500/api/excel/process \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "data.xlsx",
    "task": "異常値検出"
  }'

# ファイルの要約を取得
curl -X POST http://localhost:9500/api/excel/summary \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "data.xlsx"
  }'
```

### VisiDataと組み合わせて使用

```bash
# 1. VisiDataでExcelを開く（超高速）
vd data.xlsx

# 2. LLMで分析（API経由）
curl -X POST http://localhost:9500/api/excel/process \
  -H "Content-Type: application/json" \
  -d '{"file_path": "data.xlsx", "task": "異常値検出"}'

# 3. 結果を確認
cat data_llm_analysis.txt
```

## 統合状態確認

```bash
# すべての統合の状態を確認
curl http://localhost:9500/api/integrations/status

# excel_llm統合の状態を確認
curl http://localhost:9500/api/integrations/status | jq '.integrations.excel_llm'
```

## ワークフロー例

### 1. 異常値検出ワークフロー

```bash
# 1. VisiDataでExcelを確認
vd data.xlsx

# 2. LLMで異常値を検出
curl -X POST http://localhost:9500/api/excel/process \
  -H "Content-Type: application/json" \
  -d '{"file_path": "data.xlsx", "task": "異常値検出"}'

# 3. 結果を確認
cat data_llm_analysis.txt
```

### 2. 定期分析ワークフロー（cron/n8n）

```python
import requests
import schedule
import time

def analyze_excel():
    response = requests.post(
        "http://localhost:9500/api/excel/process",
        json={
            "file_path": "/path/to/daily_data.xlsx",
            "task": "集計分析"
        }
    )
    if response.json()["success"]:
        print("分析完了:", response.json()["output_file"])

# 毎日9時に実行
schedule.every().day.at("09:00").do(analyze_excel)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 3. Slack通知と組み合わせ

```python
import requests

# Excel分析
excel_result = requests.post(
    "http://localhost:9500/api/excel/process",
    json={
        "file_path": "data.xlsx",
        "task": "異常値検出"
    }
).json()

# Slackに通知（ManaOS統合API経由）
if excel_result["success"]:
    requests.post(
        "http://localhost:9500/api/notification/send",
        json={
            "channel": "slack",
            "message": f"Excel分析完了: {excel_result['output_file']}",
            "attachments": [excel_result["output_file"]]
        }
    )
```

## 環境変数

- `OLLAMA_URL`: Ollama APIのURL（デフォルト: `http://localhost:11434`）
- `OLLAMA_MODEL`: 使用するモデル名（デフォルト: `qwen2.5:7b`）

## トラブルシューティング

### Excel/LLM処理が利用できない

```bash
# 1. Ollamaサービスが起動しているか確認
curl http://localhost:11434/api/tags

# 2. 統合状態を確認
curl http://localhost:9500/api/integrations/status

# 3. ログを確認
# unified_api_server.pyのログを確認
```

### ファイルが見つからない

- ファイルパスは絶対パスを使用することを推奨
- 相対パスの場合は、統合APIサーバーの作業ディレクトリからの相対パス

### LLM処理が失敗する

- Ollamaサービスが起動しているか確認
- モデルがインストールされているか確認: `ollama list`
- タイムアウト設定を確認（デフォルト: 120秒）

## n8nワークフローとの統合

n8nワークフローテンプレートが利用可能です：

- `n8n_workflows/excel_llm_integration_workflow.json` - Excel/LLM処理ワークフロー
- `EXCEL_LLM_N8N_INTEGRATION.md` - n8n統合ガイド

詳細は `EXCEL_LLM_N8N_INTEGRATION.md` を参照してください。

## 次のステップ

1. **n8nワークフローとの統合** ✅
   - n8nワークフローテンプレート作成済み
   - 詳細: `EXCEL_LLM_N8N_INTEGRATION.md`

2. **Slack/Notionへの自動送信**
   - 分析結果を自動的にSlack/Notionに送信（n8nワークフローに含まれています）

3. **定期実行のスケジューリング**
   - cronやn8nで定期実行（n8nワークフローで実装可能）

4. **複数ファイルの一括処理**
   - 複数のExcelファイルを一括で処理
