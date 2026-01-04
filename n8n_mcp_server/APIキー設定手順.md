# n8n APIキー設定手順

## 方法1: ブラウザから取得（推奨）

### ステップ1: n8nのWeb UIにアクセス

ブラウザで以下のURLを開いてください：
```
http://100.93.120.33:5678
```

### ステップ2: ログイン

n8nのアカウントでログインしてください。

### ステップ3: APIキーを作成

1. 左上のメニュー（≡）をクリック
2. **Settings** を選択
3. **API** を選択
4. **Create API Key** をクリック
5. APIキー名を入力（例: `MCP Server`）
6. **Create** をクリック
7. 表示されたAPIキーをコピー（**重要**: この画面を閉じると再表示できません）

### ステップ4: APIキーを設定

コピーしたAPIキーを以下のいずれかの方法で設定してください：

#### 方法A: PowerShellスクリプトを使用

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\n8n_mcp_server\set_api_key_manual.ps1 -ApiKey "ここにAPIキーを貼り付け"
```

#### 方法B: 設定ファイルを直接編集

```powershell
notepad "$env:USERPROFILE\.cursor\mcp.json"
```

以下の部分を探して、`""` の部分にAPIキーを設定：

```json
"n8n": {
  "env": {
    "N8N_API_KEY": "ここにAPIキーを貼り付け"
  }
}
```

### ステップ5: Cursorを再起動

APIキーを設定したら、Cursorを完全に再起動してください。

---

## 方法2: 既存のAPIキーを確認（このはサーバー）

このはサーバーで既存のAPIキーがあるか確認：

```bash
ssh konoha
docker exec trinity-n8n env | grep -i api
```

---

## 確認方法

APIキーを設定した後、以下のコマンドで確認できます：

```powershell
Get-Content "$env:USERPROFILE\.cursor\mcp.json" | ConvertFrom-Json | Select-Object -ExpandProperty mcpServers | Select-Object -ExpandProperty n8n | Select-Object -ExpandProperty env
```

`N8N_API_KEY` が設定されていることを確認してください。

---

## トラブルシューティング

### ブラウザで接続できない場合

1. **キャッシュをクリア**
   - `Ctrl + Shift + Delete` でキャッシュをクリア
   - またはシークレットモードで試す

2. **別のブラウザで試す**
   - Chrome、Edge、Firefoxなど

3. **n8nコンテナの状態を確認**
   ```bash
   ssh konoha
   docker ps | grep n8n
   docker logs trinity-n8n --tail 50
   ```

### APIキーが無効な場合

1. n8nのWeb UIで新しいAPIキーを作成
2. 古いAPIキーを削除
3. 新しいAPIキーを設定

---

## 次のステップ

APIキーを設定してCursorを再起動したら：

1. CursorでMCPサーバーに接続できるか確認
2. `n8n_import_workflow` ツールが使えるか確認
3. ワークフローをインポート
















