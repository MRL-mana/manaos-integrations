# N8N APIキー問題 完全解決手順

## 🔍 問題の原因

何度もAPIキーを設定しているのに401エラーが発生する原因：

1. **ローカルN8N（ポート5679）が応答していない可能性**
   - タイムアウトエラーが発生
   - N8Nプロセスが実際に起動しているか確認が必要

2. **APIキーが異なるインスタンス用に発行されている可能性**
   - ポート5679（ローカル）用のAPIキーが必要
   - ポート5678（Docker）用のAPIキーとは別

3. **MCP設定ファイルとスクリプト内のAPIキーが不一致**
   - `list_workflows_detail.py`に古いAPIキーがハードコードされている
   - MCP設定ファイルのAPIキーと異なる

---

## ✅ 解決手順（ステップバイステップ）

### Step 1: N8Nの起動状態を確認

```powershell
# ローカルN8Nのプロセス確認
Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { 
    try { 
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -like "*n8n*"
    } catch { 
        $false 
    }
}

# ポート5679の確認
Test-NetConnection -ComputerName localhost -Port 5679

# ヘルスチェック
curl.exe http://localhost:5679/healthz
```

**期待される結果:**
- N8Nプロセスが起動している
- ポート5679がリッスンしている
- ヘルスチェックが `{"status":"ok"}` を返す

**もしN8Nが起動していない場合:**
```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\start_n8n_local.ps1
```

---

### Step 2: N8NのWeb UIにアクセスしてAPIキーを作成

#### 2-1. ブラウザでN8Nを開く

```powershell
# ローカルN8N（ポート5679）を開く
Start-Process "http://localhost:5679"
```

#### 2-2. ログイン

- 既存のアカウントでログイン
- 初回アクセスの場合はアカウント作成

#### 2-3. APIキーを作成

1. **右上のユーザーアイコン**をクリック
2. **Settings** を選択
3. 左メニューから **API** を選択
4. **Create API Key** をクリック
5. APIキー名を入力（例: `MCP Server Local`）
6. **Create** をクリック
7. **⚠️ 重要**: 表示されたAPIキーを**すぐにコピー**（この画面を閉じると再表示できません）

---

### Step 3: APIキーをMCP設定ファイルに設定

#### 方法A: PowerShellスクリプトを使用（推奨）

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\n8n_mcp_server\set_api_key_manual.ps1 -ApiKey "ここにコピーしたAPIキーを貼り付け" -BaseUrl "http://localhost:5679"
```

#### 方法B: 手動で設定ファイルを編集

```powershell
# 設定ファイルを開く
$mcpConfigPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
notepad $mcpConfigPath
```

以下の部分を更新：
```json
{
  "mcpServers": {
    "n8n": {
      "command": "python",
      "args": ["-m", "n8n_mcp_server.server"],
      "cwd": "C:\\Users\\mana4\\Desktop\\manaos_integrations",
      "env": {
        "N8N_API_KEY": "ここに新しいAPIキーを貼り付け",
        "N8N_BASE_URL": "http://localhost:5679",
        "PYTHONPATH": "C:\\Users\\mana4\\Desktop\\manaos_integrations"
      }
    }
  }
}
```

---

### Step 4: APIキーの動作確認

```powershell
# 環境変数を設定してテスト
$env:N8N_API_KEY = "ここに新しいAPIキー"
$env:N8N_BASE_URL = "http://localhost:5679"

# テスト実行
python n8n_mcp_server\test_mcp_connection.py
```

**期待される結果:**
```
[OK] n8nへの接続成功
[OK] ワークフロー数: X
```

**もし401エラーが続く場合:**
- APIキーが正しくコピーされているか確認
- N8NのWeb UIでAPIキーが作成されているか確認
- N8Nを再起動してみる

---

### Step 5: Cursorを再起動

MCP設定を反映するため、**Cursorを完全に再起動**してください。

1. Cursorを閉じる
2. 数秒待つ
3. Cursorを再度開く

---

### Step 6: MCPツールの動作確認

Cursorで以下のように試してください：

```
n8n_list_workflows を使ってワークフロー一覧を取得してください
```

---

## 🔧 トラブルシューティング

### 問題1: N8Nが起動しない

**症状:**
- ポート5679に接続できない
- プロセスが見つからない

**解決方法:**
```powershell
# N8Nを起動
cd C:\Users\mana4\Desktop\manaos_integrations
.\start_n8n_local.ps1

# 別のウィンドウで起動する場合
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\mana4\Desktop\manaos_integrations'; `$env:N8N_PORT='5679'; n8n start --port 5679"
```

---

### 問題2: APIキーを作成できない

**症状:**
- Settings → API にアクセスできない
- Create API Key ボタンが表示されない

**解決方法:**
1. N8Nのバージョンを確認（v1.0以上が必要）
2. 管理者権限でログインしているか確認
3. N8Nを再起動

---

### 問題3: APIキーを設定しても401エラーが続く

**症状:**
- APIキーを設定したが、まだ401エラー

**確認項目:**

1. **APIキーが正しく設定されているか確認**
   ```powershell
   $mcpConfigPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
   $config = Get-Content $mcpConfigPath | ConvertFrom-Json
   $config.mcpServers.n8n.env.N8N_API_KEY
   ```

2. **N8N_BASE_URLが正しいか確認**
   ```powershell
   $config.mcpServers.n8n.env.N8N_BASE_URL
   ```
   期待値: `http://localhost:5679`

3. **N8Nが実際に起動しているか確認**
   ```powershell
   curl.exe http://localhost:5679/healthz
   ```

4. **APIキーが有効か直接テスト**
   ```powershell
   $env:N8N_API_KEY = "your-api-key"
   $env:N8N_BASE_URL = "http://localhost:5679"
   python -c "import requests; import os; r = requests.get(f'{os.getenv(\"N8N_BASE_URL\")}/api/v1/workflows', headers={'X-N8N-API-KEY': os.getenv('N8N_API_KEY')}); print(f'Status: {r.status_code}'); print(r.text[:200])"
   ```

---

### 問題4: スクリプト内のハードコードされたAPIキー

**問題:**
- `list_workflows_detail.py`などに古いAPIキーがハードコードされている

**解決方法:**
環境変数から読み込むように修正（既に修正済みの場合は問題なし）

---

## 📋 チェックリスト

- [ ] N8Nが起動している（ポート5679）
- [ ] N8NのWeb UIにアクセスできる
- [ ] 新しいAPIキーを作成した
- [ ] APIキーをコピーした
- [ ] MCP設定ファイルを更新した
- [ ] APIキーの動作確認が成功した
- [ ] Cursorを再起動した
- [ ] MCPツールが動作する

---

## 💡 重要なポイント

1. **APIキーは一度しか表示されない** - 必ずコピーして保存
2. **N8N_BASE_URLはポート5679** - ローカルN8Nに接続
3. **Cursorの再起動が必要** - MCP設定を反映するため
4. **環境変数とMCP設定ファイルの両方を確認** - 不一致がないか確認

---

## 🎯 最終確認

すべてのステップを完了したら、以下で最終確認：

```powershell
# 1. N8Nの状態確認
python n8n_mcp_server\check_n8n_status.py

# 2. APIキーの動作確認
python n8n_mcp_server\test_mcp_connection.py

# 3. ワークフロー一覧取得
python n8n_mcp_server\list_workflows_detail.py
```

すべて成功すれば、MCPツールが正常に動作します！
