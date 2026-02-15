# ManaOS クイックリファレンス

## 🚀 1分で起動

### VSCode/Cursor起動（推奨）
```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: すべてのサービスを起動"
```

### コマンドライン
```powershell
cd C:\Users\mana4\Desktop
.\.venv\Scripts\python.exe manaos_integrations\start_vscode_cursor_services.py
```

## 🔍 ヘルスチェック

### すべてのサービス
```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: サービスヘルスチェック"
```

または

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python check_services_health.py
```

### 個別確認（PowerShell）
```powershell
# Unified API (メインエントリーポイント)
Invoke-RestMethod http://127.0.0.1:9510/health

# MRL Memory
Invoke-RestMethod http://127.0.0.1:5103/health

# Learning System
Invoke-RestMethod http://127.0.0.1:5104/health

# LLM Routing
Invoke-RestMethod http://127.0.0.1:5111/health
```

## ⚡ サービス一覧

| サービス | ポート | URL |
|---------|--------|-----|
| Unified API | 9510 | http://127.0.0.1:9510 |
| MRL Memory | 5103 | http://127.0.0.1:5103 |
| Learning System | 5104 | http://127.0.0.1:5104 |
| LLM Routing | 5111 | http://127.0.0.1:5111 |

## 🛠️ トラブルシューティング

### サービスが応答しない
```powershell
# 30秒待ってから再チェック
Start-Sleep -Seconds 30
python check_services_health.py
```

### ポート競合確認
```powershell
netstat -ano | findstr ":9510"
netstat -ano | findstr ":5103"
netstat -ano | findstr ":5104"
netstat -ano | findstr ":5111"
```

### 強制停止して再起動
```powershell
# すべてのManaOSプロセスを停止
Get-Process python | Where-Object { $_.CommandLine -like "*manaos*" } | Stop-Process

# 再起動
.\.venv\Scripts\python.exe manaos_integrations\start_vscode_cursor_services.py
```

## 📚 詳細ドキュメント

- **起動ガイド**: [STARTUP_GUIDE.md](STARTUP_GUIDE.md)
- **設定ファイル**: 
  - Cursor: `~/.cursor/mcp.json`
  - VSCode: `~/.vscode/settings.json`

## 🆘 よくある質問

**Q: 起動に時間がかかる**  
A: 初期化に10-30秒かかります。ヘルスチェックは自動でリトライします。

**Q: 一部のサービスだけ起動したい**  
A: 個別タスクを使用:
- "ManaOS: MRLメモリを起動"
- "ManaOS: 学習システムを起動"
- "ManaOS: LLMルーティングを起動"
- "ManaOS: 統合APIを起動"

**Q: 停止方法は？**  
A: 起動ターミナルで `Ctrl+C` を押す

---

**最終更新**: 2026年2月7日
