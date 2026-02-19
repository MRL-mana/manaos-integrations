# ManaOS サービス起動ガイド

## 📋 概要

ManaOSの4つのコアサービスを起動・管理する公式ガイドです。

### サービス一覧

| サービス名 | ポート | 説明 |
|-----------|--------|------|
| MRL Memory | 5103 | 記憶管理システム |
| Learning System | 5104 | 学習・自動改善システム |
| LLM Routing | 5111 | LLMルーティング |
| OpenAI Router | 5211 | OpenAI互換ルーター（`auto-local`） |
| Unified API | 9502 | 統合API（メインエントリーポイント） |

## 🚀 起動方法

### 方法1: VSCode/Cursorタスク（推奨）

1. VSCode/Cursorで `Ctrl+Shift+P` を押す
2. "Tasks: Run Task" を選択
3. "ManaOS: すべてのサービスを起動" を選択

```
タスク実行後、自動的にヘルスチェックが実行されます。
すべてのサービスが ✅ と表示されれば起動成功です。
```

### 方法2: コマンドライン

```powershell
cd C:\Users\mana4\Desktop
.\.venv\Scripts\python.exe manaos_integrations\start_vscode_cursor_services.py
```

## 🔍 ヘルスチェック

起動後、すべてのサービスが正常稼働しているか確認します：

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python check_services_health.py
```

### 期待される出力

```
============================================================
🔍 ManaOSサービスヘルスチェック
============================================================
✅ MRL Memory           (port 5103): OK
✅ Learning System      (port 5104): OK
✅ LLM Routing          (port 5111): OK
✅ Unified API          (port 9502): OK
============================================================
✅ すべてのサービスが正常稼働中
============================================================
```

## ⚠️ トラブルシューティング

### サービスが応答しない場合

1. **初期化待ち**: サービスが起動しても初期化に10-30秒かかる場合があります
   ```powershell
   # 30秒待ってから再チェック
   Start-Sleep -Seconds 30
   python check_services_health.py
   ```

2. **ポート競合**: 別のプロセスがポートを使用している可能性
   ```powershell
   # ポート使用状況を確認
   netstat -ano | findstr ":9502"
   netstat -ano | findstr ":5103"
   netstat -ano | findstr ":5104"
   netstat -ano | findstr ":5111"
   ```

3. **プロセス確認**: サービスが実際に起動しているか確認
   ```powershell
   Get-Process python | Where-Object { $_.CommandLine -like "*manaos*" }
   ```

4. **再起動**: すべてのサービスを停止して再起動
   ```powershell
   # すべてのManaOS Pythonプロセスを停止
   Get-Process python | Where-Object { $_.CommandLine -like "*manaos*" } | Stop-Process
   
   # 再起動
   .\.venv\Scripts\python.exe manaos_integrations\start_vscode_cursor_services.py
   ```

### 個別サービスの手動起動

問題の切り分けのため、個別にサービスを起動できます：

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations

# MRL Memory
python -m mrl_memory_integration

# Learning System
python -m learning_system_api

# LLM Routing
python -m llm_routing_mcp_server.server

# Unified API
python -m unified_api_server
```

## 📊 動作確認

### APIエンドポイントテスト

#### Unified API (9502)

```powershell
# ヘルスチェック（軽量）
Invoke-RestMethod -Uri "http://127.0.0.1:9502/health"

# レディネスチェック（完全初期化確認）
Invoke-RestMethod -Uri "http://127.0.0.1:9502/ready"

# 統合ステータス
Invoke-RestMethod -Uri "http://127.0.0.1:9502/api/integrations/status"
```

#### 個別サービス

```powershell
# MRL Memory
Invoke-RestMethod -Uri "http://127.0.0.1:5103/health"

# Learning System
Invoke-RestMethod -Uri "http://127.0.0.1:5104/health"

# LLM Routing
Invoke-RestMethod -Uri "http://127.0.0.1:5111/health"

# OpenAI Router
Invoke-RestMethod -Uri "http://127.0.0.1:5211/v1/models"
```

## 📁 関連ファイル

- **起動スクリプト**: `manaos_integrations/start_vscode_cursor_services.py`
- **ヘルスチェック**: `manaos_integrations/check_services_health.py`
- **VSCodeタスク**: `.vscode/tasks.json`
- **設定ファイル**: 
  - Cursor: `~/.cursor/mcp.json`
  - VSCode: `~/.vscode/settings.json`

## 🔄 定常運用

### 起動モード

ManaOSサービスは以下のモードで運用できます：

1. **開発モード**（デフォルト）: 
   - ターミナルでフォアグラウンド実行
   - ログをリアルタイムで確認
   - Ctrl+Cで停止

2. **バックグラウンドモード**:
   - タスクとして実行
   - VSCode/Cursor起動時に自動開始（オプション）

### 自動起動設定（オプション）

VSCode/Cursor起動時に自動でサービスを起動する場合：

1. `.vscode/tasks.json` の `runOptions` を設定
2. または、Windows起動時にスクリプトを実行

## 🆘 サポート

問題が解決しない場合：

1. ログファイルを確認: `manaos_integrations/logs/`
2. 環境変数を確認: `.env` ファイル
3. Python環境を確認: `.venv` の状態

---

**最終更新**: 2026年2月7日  
**バージョン**: 1.0.0  
**メンテナンス**: ManaOS Integration Team
