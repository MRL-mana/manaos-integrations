# X280 API Gateway デプロイ＆起動ガイド

## ファイル転送完了 ✅

以下のファイルがX280側に転送されました：
- `C:\manaos_x280\x280_api_gateway.py`
- `C:\manaos_x280\start_x280_api_gateway.ps1`

## X280側での起動方法

### 方法1: SSH経由で起動（推奨）

```powershell
# X280にSSH接続
ssh x280

# X280側で実行
cd C:\manaos_x280
.\start_x280_api_gateway.ps1
```

### 方法2: 直接Pythonで起動

```powershell
# X280にSSH接続
ssh x280

# X280側で実行
cd C:\manaos_x280
$env:X280_API_PORT = "5120"
python x280_api_gateway.py
```

### 方法3: バックグラウンドで起動

```powershell
# X280にSSH接続
ssh x280

# X280側で実行
cd C:\manaos_x280
Start-Process powershell -ArgumentList "-File start_x280_api_gateway.ps1" -WindowStyle Hidden
```

## 接続テスト

### ローカル（X280側）から
```powershell
# X280側で実行
Invoke-RestMethod -Uri "http://localhost:5120/api/health"
```

### リモート（新PC側）から
```powershell
# 新PC側で実行
Invoke-RestMethod -Uri "http://100.127.121.20:5120/api/health"
```

## API エンドポイント確認

- ルート: `http://100.127.121.20:5120/`
- ヘルスチェック: `http://100.127.121.20:5120/api/health`
- システム情報: `http://100.127.121.20:5120/api/system/info`
- リソース情報: `http://100.127.121.20:5120/api/system/resources`
- API ドキュメント: `http://100.127.121.20:5120/docs`

## 次のステップ

1. ✅ X280側でAPI Gatewayを起動
2. ✅ 接続テストを実行
3. ⏳ ManaOS側のNode Managerから接続テスト
4. ⏳ Portal UIへの統合

## トラブルシューティング

### ポート5120が使用中
```powershell
# X280側で実行
Get-NetTCPConnection -LocalPort 5120 | Select-Object OwningProcess | ForEach-Object { Get-Process -Id $_.OwningProcess }
```

### Pythonが見つからない
```powershell
# X280側で実行
python --version
# または
py --version
```

### FastAPIがインストールされていない
```powershell
# X280側で実行
pip install fastapi uvicorn
```

