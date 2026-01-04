# n8n APIキー再取得手順

## 問題

現在のAPIキーは `"aud": "mcp-server-api"` というオーディエンス向けに発行されており、n8nの標準APIでは使用できない可能性があります。

## 解決方法

n8nのWeb UIから新しいAPIキーを作成してください。

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
5. APIキー名を入力（例: `MCP Server API`）
6. **Create** をクリック
7. **表示されたAPIキーをコピー**（重要: この画面を閉じると再表示できません）

### ステップ4: APIキーを設定

コピーしたAPIキーを以下のコマンドで設定してください：

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\n8n_mcp_server\set_api_key_manual.ps1 -ApiKey "ここに新しいAPIキーを貼り付け"
```

### ステップ5: 接続確認

```powershell
python n8n_mcp_server\test_connection.py
```

Status: 200 が表示されれば成功です。

### ステップ6: Cursorを再起動

APIキーを設定したら、Cursorを再起動してください。

---

## 代替方法: 既存のAPIキーを確認

このはサーバーで既存のAPIキーがあるか確認：

```bash
ssh konoha
docker exec trinity-n8n sqlite3 /home/node/.n8n/database.sqlite "SELECT * FROM user WHERE role = 'owner' LIMIT 1;"
```

ただし、APIキーはハッシュ化されて保存されているため、直接取得はできません。

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















