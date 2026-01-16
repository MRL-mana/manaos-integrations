# VisiData + Ollama + Excel/LLM処理 完全セットアップガイド

## 概要

「入れた瞬間から元取れる」コスパ最強のExcel分析環境を一気にセットアップします。

## 推奨セットアップ手順（一気に実行）

### Windows（PowerShell）

```powershell
# 1. VisiData + Ollama セットアップ
.\setup_visidata_ollama_complete.ps1

# 2. 統合APIサーバーを再起動（統合を反映）
# 現在実行中の場合は停止してから再起動
python start_server_direct.py

# 3. 統合状態を確認
curl http://localhost:9500/api/integrations/status | python -m json.tool | Select-String "excel_llm"
```

### Linux（Bash）

```bash
# 1. VisiData + Ollama セットアップ
./setup_visidata_ollama_complete.sh

# 2. 統合APIサーバーを再起動（統合を反映）
# 現在実行中の場合は停止してから再起動
python3 start_server_direct.py

# 3. 統合状態を確認
curl http://localhost:9500/api/integrations/status | jq '.integrations.excel_llm'
```

## 動作確認

### 1. VisiDataの動作確認

```bash
# テスト用のExcelファイルを作成（簡単なサンプル）
python -c "import pandas as pd; df = pd.DataFrame({'A': [1,2,3], 'B': [4,5,6]}); df.to_excel('test.xlsx', index=False); print('test.xlsx created')"

# VisiDataで開く
vd test.xlsx
# 'q' キーで終了
```

### 2. Ollamaの動作確認

```bash
# Ollamaサービスが起動しているか確認
curl http://localhost:11434/api/tags

# モデルを確認
ollama list
```

### 3. Excel/LLM処理の動作確認

```bash
# 統合APIサーバーが起動していることを確認
curl http://localhost:9500/health

# Excel/LLM統合が有効か確認
curl http://localhost:9500/api/integrations/status | jq '.integrations.excel_llm'

# 実際にExcel分析を実行（テストファイルを使用）
curl -X POST http://localhost:9500/api/excel/process \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "test.xlsx",
    "task": "異常値検出"
  }'
```

### 4. n8nワークフローのインポート（オプション）

```bash
# n8nを開く
# http://localhost:5678

# ワークフローをインポート
# Workflows → Import from File
# n8n_workflows/excel_llm_integration_workflow.json を選択
```

## 推奨ワークフロー

### 日常的な使用

1. **VisiDataでExcelを確認**（超高速）
   ```bash
   vd data.xlsx
   ```

2. **LLMで分析**（API経由）
   ```bash
   curl -X POST http://localhost:9500/api/excel/process \
     -H "Content-Type: application/json" \
     -d '{"file_path": "data.xlsx", "task": "異常値検出"}'
   ```

3. **結果を確認**
   ```bash
   cat data_llm_analysis.txt
   ```

### n8nワークフロー経由（自動化）

1. **Webhook経由で実行**
   ```bash
   curl -X POST http://localhost:5678/webhook/excel-llm-process \
     -H "Content-Type: application/json" \
     -d '{"file_path": "data.xlsx", "task": "異常値検出"}'
   ```

2. **自動的にSlack通知とObsidian記録が実行される**

## トラブルシューティング

### 統合APIサーバーが起動しない

```bash
# エラーログを確認
python start_server_direct.py

# ポートが使用中の場合
netstat -ano | findstr :9500  # Windows
lsof -i :9500                 # Linux
```

### Excel/LLM統合が利用できない

```bash
# 1. 統合状態を確認
curl http://localhost:9500/api/integrations/status

# 2. ログを確認
# unified_api_server.pyのログを確認

# 3. 手動で統合を確認
python -c "from excel_llm_integration import ExcelLLMIntegration; integration = ExcelLLMIntegration(); print('Available:', integration.is_available())"
```

### Ollamaサービスが起動していない

```bash
# Windows
ollama serve

# Linux
systemctl start ollama
# または
ollama serve
```

## 完了確認

すべてのステップが完了したら、以下を確認してください：

1. ✅ VisiDataがインストールされている: `vd --version`
2. ✅ Ollamaサービスが起動している: `curl http://localhost:11434/api/tags`
3. ✅ 統合APIサーバーが起動している: `curl http://localhost:9500/health`
4. ✅ Excel/LLM統合が有効: `curl http://localhost:9500/api/integrations/status | jq '.integrations.excel_llm'`
5. ✅ n8nワークフローがインポートされている（オプション）

## 次のステップ

1. **実際のExcelファイルでテスト**
   - 自分のExcelファイルで動作確認

2. **n8nワークフローをカスタマイズ**
   - 独自のワークフローを構築

3. **定期実行の設定**
   - n8nで定期実行を設定

4. **複数ファイルの一括処理**
   - 複数のExcelファイルを一括で処理
