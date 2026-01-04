# ManaOS トラブルシューティングガイド

**バージョン**: 1.0  
**最終更新**: 2025-01-28

---

## 📋 目次

1. [よくある問題](#よくある問題)
2. [エラー対処法](#エラー対処法)
3. [パフォーマンス問題](#パフォーマンス問題)
4. [ログの確認方法](#ログの確認方法)

---

## よくある問題

### 1. サービスが起動しない

**症状**: ポートが開いていない、または応答がない

**確認方法**:
```powershell
# ポート確認
Test-NetConnection -ComputerName localhost -Port 5100

# プロセス確認
Get-Process python* | Where-Object {$_.Path -like "*manaos_integrations*"}
```

**解決方法**:
1. ログを確認
   ```powershell
   Get-Content logs\intent_router.log -Tail 50
   ```

2. 手動で起動してエラーを確認
   ```powershell
   python intent_router.py
   ```

3. 依存パッケージを確認
   ```powershell
   pip install -r requirements.txt
   ```

---

### 2. Ollama接続エラー

**症状**: LLMベースの機能が動作しない

**確認方法**:
```powershell
# Ollama確認
Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing

# モデル確認
ollama list
```

**解決方法**:
1. Ollamaが起動しているか確認
   ```powershell
   ollama serve
   ```

2. 必要なモデルをインストール
   ```powershell
   ollama pull llama3.2:3b
   ```

---

### 3. タイムアウトエラー

**症状**: Task PlannerやTask Criticがタイムアウトする

**解決方法**:
1. タイムアウト設定を確認
   ```powershell
   Get-Content manaos_timeout_config.json
   ```

2. 環境変数でタイムアウトを延長
   ```powershell
   $env:MANAOS_TIMEOUT_LLM_CALL = "60.0"
   ```

3. 軽量モデルを使用
   ```json
   {
     "model": "llama3.2:3b"
   }
   ```

---

### 4. SSOT Generatorが停止する

**症状**: SSOTファイルが更新されない

**解決方法**:
1. SSOT Monitorを起動
   ```powershell
   python ssot_monitor.py
   ```

2. 手動でSSOT Generatorを再起動
   ```powershell
   python ssot_generator.py
   ```

---

## エラー対処法

### Network Errors

**エラーコード**: `NET_CONNECTION_ERROR`, `NET_TIMEOUT_ERROR`

**対処法**:
1. サービスが起動しているか確認
2. ファイアウォール設定を確認
3. ネットワーク接続を確認

### Timeout Errors

**エラーコード**: `TIM_TIMEOUT`

**対処法**:
1. タイムアウト設定を延長
2. リソース使用状況を確認
3. 軽量モデルを使用

### Validation Errors

**エラーコード**: `VALIDATION_ERROR`

**対処法**:
1. 入力値を確認
2. 設定ファイルを確認
3. スキーマ定義を確認

---

## パフォーマンス問題

### CPU使用率が高い

**確認方法**:
```powershell
# SSOTで確認
Invoke-WebRequest -Uri "http://localhost:5120/api/ssot" -UseBasicParsing | ConvertFrom-Json | Select-Object -ExpandProperty system
```

**対処法**:
1. 不要なサービスを停止
2. LLMモデルを軽量化
3. 並行処理数を制限

### メモリ使用率が高い

**確認方法**:
```powershell
# プロセスメモリ確認
Get-Process python* | Select-Object Name, @{Name="Memory(MB)";Expression={[math]::Round($_.WS/1MB,2)}}
```

**対処法**:
1. 不要なサービスを停止
2. ログローテーションを確認
3. メモリリークを確認

---

## ログの確認方法

### ログファイルの場所

```
manaos_integrations/logs/
├── intent_router.log
├── intent_router_error.log
├── task_planner.log
└── ...
```

### ログの確認

```powershell
# 最新50行を確認
Get-Content logs\intent_router.log -Tail 50

# エラーログを確認
Get-Content logs\intent_router_error.log -Tail 50

# 特定のエラーを検索
Select-String -Path logs\*.log -Pattern "ERROR"
```

---

## 緊急時の対処法

### 全サービスを停止

```powershell
.\stop_all_services.ps1
```

### 全サービスを再起動

```powershell
.\stop_all_services.ps1
.\start_all_services.ps1
```

### プロセスを強制終了

```powershell
# 特定のプロセスを終了
Stop-Process -Name python -Force

# 全Pythonプロセスを終了（注意）
Get-Process python | Stop-Process -Force
```

---

**バージョン**: 1.0  
**最終更新**: 2025-01-28

