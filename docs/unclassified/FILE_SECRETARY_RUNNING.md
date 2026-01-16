# File Secretary 運用開始

**開始日時**: 2026-01-03  
**状態**: 運用中

---

## 🚀 起動状況

### 実行中サービス

- ✅ **Indexer**: ファイル監視・インデックス実行中
- ✅ **APIサーバー**: ポート5120で実行中

### アクセス方法

- **API**: http://localhost:5120
- **INBOX**: `C:\Users\mana4\Desktop\manaos_integrations\00_INBOX`
- **データベース**: `file_secretary.db`

---

## 💬 Slack統合

Slack Integrationを起動すると、Slackから直接操作できます。

### 起動方法

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
$env:PORT="5114"
$env:FILE_SECRETARY_URL="http://localhost:5120"
$env:ORCHESTRATOR_URL="http://localhost:5106"
python slack_integration.py
```

### 使用可能なコマンド

- `Inboxどう？` - INBOX状況確認
- `終わった` - ファイル整理実行
- `戻して` - ファイル復元
- `探して：◯◯` - ファイル検索

---

## 📊 状態確認

### APIヘルスチェック

```bash
curl http://localhost:5120/health
```

### INBOX状況確認

```bash
curl http://localhost:5120/api/inbox/status
```

### プロセス確認（Windows）

```powershell
Get-Process python | Where-Object { $_.Path -like "*Python*" }
```

---

## 🛑 停止方法

### 手動停止

```powershell
# すべてのPythonプロセスを停止
Get-Process python | Stop-Process -Force

# または、特定のPIDを停止
Stop-Process -Id <PID> -Force
```

### 運用管理スクリプト使用

```bash
python file_secretary_manager.py stop
```

---

## 📝 ログ確認

ログファイルは `logs/` ディレクトリに保存されます。

```bash
# 最新のログを確認
Get-Content logs/file_secretary_api.log -Tail 50

# エラーログのみ確認
Select-String -Path logs/*.log -Pattern "ERROR"
```

---

## 🎯 次のステップ

1. **Slack Integration起動** - Slackから操作可能に
2. **ファイルをINBOXに放り込む** - 自動検知・インデックス
3. **Slackで「Inboxどう？」** - 状況確認
4. **「終わった」で整理** - 自動タグ付け・alias生成

---

**File Secretaryシステムは運用中です！** 🎉






















