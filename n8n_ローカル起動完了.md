# n8n ローカル起動完了

## 起動状況

母艦（新PC）でn8nをポート5679で起動しました。

## アクセス方法

ブラウザで以下のURLを開いてください：
```
http://localhost:5679
```

## 初回セットアップ

1. **アカウント作成**
   - 初回アクセス時にアカウント作成画面が表示されます
   - ユーザー名、メールアドレス、パスワードを入力してください

2. **APIキーの作成**
   - ログイン後、左上のメニュー（≡）をクリック
   - **Settings** → **API** → **Create API Key**
   - APIキー名を入力（例: `MCP Server API`）
   - **Create** をクリック
   - **表示されたAPIキーをコピー**（重要: この画面を閉じると再表示できません）

3. **MCP設定の更新**
   - APIキーを取得したら、以下のコマンドで設定：
   ```powershell
   cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
   .\n8n_mcp_server\set_api_key_manual.ps1 -ApiKey "ここにAPIキーを貼り付け"
   ```

4. **Cursorを再起動**
   - APIキーを設定したら、Cursorを再起動してください

## 起動・停止方法

### 起動
```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_n8n_local.ps1
```

### 停止
- ターミナルで `Ctrl+C` を押す
- または、以下のコマンドでプロセスを終了：
```powershell
Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*n8n*" } | Stop-Process -Force
```

## データ保存場所

n8nのデータは以下の場所に保存されます：
```
%USERPROFILE%\.n8n
```

## トラブルシューティング

### ポート5679が使用中
```powershell
# 既存のプロセスを確認
Get-NetTCPConnection -LocalPort 5679

# プロセスを終了
Get-Process -Name node | Where-Object { $_.Path -like "*n8n*" } | Stop-Process -Force
```

### n8nが起動しない
```powershell
# ログを確認
n8n start --port 5679 --log-level=debug
```

### データディレクトリの問題
```powershell
# データディレクトリを確認
Get-ChildItem "$env:USERPROFILE\.n8n"
```

## 次のステップ

1. ✅ n8nのWeb UIにアクセス
2. ⏳ アカウント作成
3. ⏳ APIキーを取得
4. ⏳ MCP設定を更新
5. ⏳ Cursorを再起動
6. ⏳ ワークフローをインポート















