# 🔗 ManaOS MCP統合テスト ガイド

## 📋 現在のサービス状態

| サービス | ポート | PID | 状態 |
|---------|--------|-----|------|
| MRL Memory | 5103 | ✅ Python | Listen |
| Learning System | 5104 | ✅ Python | Listen |
| LLM Routing | 5111 | ✅ Python | Listen |
| Unified API | 9500 | ✅ Python | Listen (初期化中) |

## 🔌 MCP接続設定

### 1. Cursor での MCP設定

**ファイルパス:** `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "manaos-memory": {
      "url": "http://127.0.0.1:5103"
    },
    "manaos-learning": {
      "url": "http://127.0.0.1:5104"
    },
    "manaos-llm-routing": {
      "url": "http://127.0.0.1:5111"
    },
    "manaos-unified-api": {
      "url": "http://127.0.0.1:9500"
    }
  }
}
```

**設定後の手順:**
1. Cursor を再起動
2. Command Palette (`Ctrl+Shift+P`) → "MCP: Restart"
3. MCPサーバー一覧を確認
4. 各サーバーが "✅ Connected" と表示されることを確認

### 2. VSCode での MCP設定

**ファイルパス:** `~/.vscode/settings.json` の拡張形式

```json
{
  "mcpServers": {
    "manaos-memory": {
      "url": "http://127.0.0.1:5103"
    },
    "manaos-learning": {
      "url": "http://127.0.0.1:5104"
    },
    "manaos-llm-routing": {
      "url": "http://127.0.0.1:5111"
    },
    "manaos-unified-api": {
      "url": "http://127.0.0.1:9500"
    }
  }
}
```

**設定後の手順:**
1. GitHub Copilot チャットを開く
2. `/` コマンドで ManaOS サービスを検索
3. ツールが一覧に表示されることを確認

## ✅ 接続テスト


### Pythonスクリプトでのテスト

```python
import requests

services = {
    "MRL Memory": "http://127.0.0.1:5103",
    "Learning System": "http://127.0.0.1:5104",
    "LLM Routing": "http://127.0.0.1:5111",
    "Unified API": "http://127.0.0.1:9500"
}

for name, url in services.items():
    try:
        response = requests.get(f"{url}/health", timeout=3)
        print(f"[OK] {name}: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {name}: {str(e)[:50]}")
```

### PowerShell でのテスト

```powershell
$services = @{
    "MRL Memory" = "http://127.0.0.1:5103/health"
    "Learning System" = "http://127.0.0.1:5104/health"
    "LLM Routing" = "http://127.0.0.1:5111/health"
    "Unified API" = "http://127.0.0.1:9500/health"
}

foreach ($service in $services.GetEnumerator()) {
    try {
        $response = Invoke-WebRequest -Uri $service.Value -TimeoutSec 3
        Write-Host "[OK] $($service.Key): $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] $($service.Key): $($_.Exception.Message)" -ForegroundColor Red
    }
}
```

## 🔧 トラブルシューティング

### 症状: "Connection refused"

**原因:** サービスがポートをリッスンしていない

**解決策:**
```powershell
# サービス再起動
Get-Process python | Stop-Process -Force
Start-Sleep -Seconds 5
python c:\Users\mana4\Desktop\manaos_integrations\start_vscode_cursor_services.py
```

### 症状: "Timeout"

**原因:** サービスが初期化中 (特にUnified API)

**解決策:**
- さらに 30-60秒待機
- /ready エンドポイントで初期化状態確認 (9500のみ)

### 症状: Cursor/VSCode で MCP が表示されない

**原因:**
- mcp.json の形式が無効
- MCPサーバーが起動していない
- ポースト指定間違い

**解決策:**
1. `mcp.json` を JSON バリデーター（例：https://jsonlint.com/）で確認
2. PowerShell で `netstat -ano | findstr :5103` でポートを確認
3. Cursor/VSCode キャッシュをクリア

## 📝 MCP ツール使用例

### 1. MRL Memory からメモリ検索

```
@manaos-memory で以下を尋ねる：
"プロジェクト X について最近のメモを検索してください"
```

### 2. Learning System で学習データ取得

```
@manaos-learning で以下を尋ねる：
"過去の改善提案 トップ5 を提示してください"
```

### 3. LLM Routing で最適モデル選択

```
@manaos-llm-routing で以下を尋ねる：
"次のクエリに最適な LLM を推奨してください: [質問内容]"
```

### 4. Unified API で統合処理

```
@manaos-unified-api で以下を尋ねる：
"Google Drive から特定フォルダを同期してください"
```

## 🚀 自動起動確認

次のログイン時に自動起動される Task Scheduler タスク：

**タスク名:** ManaOS-Services

**トリガー:** AtLogOn (ユーザーログイン時)

**実行内容:**
1. `wscript.exe` が `start_manaos_silent.vbs` を実行（無音）
2. VBScript が `python start_vscode_cursor_services.py` を実行
3. 4つのManaOSサービスが起動

---

**最後の確認日時:** 2026-02-08 13:32:00  
**ステータス:** ✅ 全サービス Ready
