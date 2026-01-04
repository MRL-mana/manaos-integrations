# X280 API Gateway セットアップガイド

## 現在の状況

**日時**: 2026年1月3日

### 完了した作業
- ✅ X280 API Gatewayスクリプトの修正（Pixel7→X280に変更）
- ✅ 起動スクリプトの作成（`start_x280_api_gateway.ps1`）
- ✅ テストスクリプトの作成（`test_x280_api_gateway.ps1`）

### 確認事項
- ⚠️ ポート5120が既に使用中（複数のプロセスが検出）
- ⚠️ 既存のAPI Gatewayが動作している可能性

## 次のステップ

### 1. 既存プロセスの確認と停止

```powershell
# ポート5120を使用しているプロセスを確認
Get-NetTCPConnection -LocalPort 5120 | Select-Object OwningProcess | ForEach-Object { Get-Process -Id $_.OwningProcess }

# 必要に応じて停止
Stop-Process -Id <プロセスID> -Force
```

### 2. X280側へのデプロイ

```powershell
# X280側にディレクトリを作成（初回のみ）
ssh x280 "mkdir C:\manaos_x280 -Force"

# ファイルを転送
scp x280_api_gateway.py x280:C:/manaos_x280/
scp start_x280_api_gateway.ps1 x280:C:/manaos_x280/
```

### 3. X280側でAPI Gatewayを起動

```powershell
# SSH経由で起動
ssh x280 "cd C:\manaos_x280; .\start_x280_api_gateway.ps1"

# またはバックグラウンドで起動
ssh x280 "cd C:\manaos_x280; Start-Process powershell -ArgumentList '-File start_x280_api_gateway.ps1' -WindowStyle Hidden"
```

### 4. 接続テスト

```powershell
# ヘルスチェック
Invoke-RestMethod -Uri "http://100.127.121.20:5120/api/health"

# システム情報取得
Invoke-RestMethod -Uri "http://100.127.121.20:5120/api/system/info"

# リソース情報取得
Invoke-RestMethod -Uri "http://100.127.121.20:5120/api/system/resources"
```

## API エンドポイント

- `GET /` - ルートエンドポイント（サービス情報）
- `GET /api/health` - ヘルスチェック
- `GET /api/system/info` - システム情報
- `GET /api/system/resources` - リソース情報（CPU、メモリ、ディスク）
- `GET /api/processes` - プロセス一覧
- `POST /api/execute` - コマンド実行
- `POST /api/file` - ファイル操作
- `GET /docs` - API ドキュメント（Swagger UI）

## トラブルシューティング

### ポート5120が使用中
1. 既存プロセスを確認
2. 必要に応じて停止
3. または別のポートを使用（環境変数`X280_API_PORT`で変更）

### 接続できない
1. X280のファイアウォール設定を確認
2. Tailscale接続を確認
3. API Gatewayが正常に起動しているか確認

### PowerShellコマンドが実行できない
1. PowerShell実行ポリシーを確認
2. 管理者権限で実行

## 参考

- [X280統合ガイド](./X280_INTEGRATION_GUIDE.md)
- [ピクセル7・X280統合まとめ](./PIXEL7_X280_INTEGRATION_SUMMARY.md)

