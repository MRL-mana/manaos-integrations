# Tailscale経由でOpen WebUIにアクセスする方法

## ✅ 結論

**はい、Tailscaleで繋がっている端末からOpen WebUIを使えます！**

## 📋 前提条件

1. **Open WebUIが起動している**
   - ポート3001でリッスン中
   - Docker Composeで起動している場合、デフォルトで`0.0.0.0`でリッスンしているため、Tailscale経由でもアクセス可能

2. **Tailscaleが正常に接続されている**
   - 両方の端末が同じTailscaleネットワークに接続されている
   - Tailscale IPアドレスが取得できている

3. **ファイアウォール設定**
   - Windowsファイアウォールでポート3001が許可されている（Private/Publicプロファイル）

## 🔍 確認方法

### 1. Open WebUIの起動確認

```powershell
# ローカルで確認
Invoke-WebRequest -Uri "http://localhost:3001" -UseBasicParsing
```

### 2. Tailscale IPの確認

**ホスト側（Open WebUIが動いている端末）:**
```powershell
# Tailscale IPを確認
Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" | Select-Object IPAddress
```

**リモート側（接続する端末）:**
```powershell
# Tailscale IPを確認
Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" | Select-Object IPAddress
```

### 3. ファイアウォール設定の確認

```powershell
# ポート3001のファイアウォールルールを確認
netsh advfirewall firewall show rule name=all | Select-String "3001"
```

## 🚀 アクセス方法

### リモート端末からアクセス

1. **ホスト側のTailscale IPを確認**
   - 例: `100.127.121.20`

2. **ブラウザでアクセス**
   ```
   http://100.127.121.20:3001
   ```

### Docker Composeの場合

`docker-compose.always-ready-llm.yml`の設定では、すでに`3001:8080`でポートマッピングされているため、追加設定は不要です。

```yaml
openwebui:
  ports:
    - 3001:8080  # ホスト:コンテナ
```

この設定により、ホストマシンのすべてのネットワークインターフェース（Tailscale含む）でリッスンします。

## 🔧 トラブルシューティング

### 接続できない場合

#### 1. ファイアウォールルールの追加

```powershell
# ポート3001を許可するファイアウォールルールを追加
New-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" `
    -Direction Inbound `
    -LocalPort 3001 `
    -Protocol TCP `
    -Action Allow `
    -Profile Private,Public
```

#### 2. Dockerのポートバインディング確認

```powershell
# Dockerコンテナのポートマッピングを確認
docker ps | Select-String "open-webui"
```

#### 3. Tailscale接続確認

```powershell
# Tailscaleのステータス確認
tailscale status
```

#### 4. ネットワーク接続テスト

**リモート端末から:**
```powershell
# ホスト側のTailscale IPにping
Test-NetConnection -ComputerName 100.127.121.20 -Port 3001
```

## 📝 注意事項

1. **セキュリティ**
   - Tailscaleネットワーク内でのみアクセス可能（VPN経由）
   - 外部からは直接アクセスできない（Tailscaleが切断されていれば）

2. **パフォーマンス**
   - Tailscale経由のアクセスは、ネットワーク速度に依存します
   - ローカルネットワークより若干遅くなる可能性があります

3. **設定の永続化**
   - ファイアウォールルールは一度設定すれば永続化されます
   - Docker Composeの設定も永続化されています

## 🎯 クイックチェックスクリプト

以下のスクリプトで一括確認できます：

```powershell
# Open WebUI Tailscale アクセス確認スクリプト
Write-Host "=== Open WebUI Tailscale Access Check ===" -ForegroundColor Cyan

# 1. Open WebUI起動確認
Write-Host "`n[1/4] Checking Open WebUI..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3001" -UseBasicParsing -TimeoutSec 3
    Write-Host "[OK] Open WebUI is running" -ForegroundColor Green
} catch {
    Write-Host "[NG] Open WebUI is not accessible: $_" -ForegroundColor Red
}

# 2. Tailscale IP確認
Write-Host "`n[2/4] Checking Tailscale IP..." -ForegroundColor Yellow
$tailscaleIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" -ErrorAction SilentlyContinue).IPAddress
if ($tailscaleIP) {
    Write-Host "[OK] Tailscale IP: $tailscaleIP" -ForegroundColor Green
    Write-Host "   Access URL: http://$tailscaleIP:3001" -ForegroundColor Cyan
} else {
    Write-Host "[NG] Tailscale interface not found" -ForegroundColor Red
}

# 3. ポート3001のリッスン確認
Write-Host "`n[3/4] Checking port 3001..." -ForegroundColor Yellow
$portCheck = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "[OK] Port 3001 is listening" -ForegroundColor Green
    $portCheck | ForEach-Object {
        Write-Host "   LocalAddress: $($_.LocalAddress)" -ForegroundColor Gray
    }
} else {
    Write-Host "[NG] Port 3001 is not listening" -ForegroundColor Red
}

# 4. ファイアウォール確認
Write-Host "`n[4/4] Checking firewall..." -ForegroundColor Yellow
$firewallRule = Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*3001*" -or $_.DisplayName -like "*Open WebUI*" }
if ($firewallRule) {
    Write-Host "[OK] Firewall rule found" -ForegroundColor Green
} else {
    Write-Host "[WARN] Firewall rule not found (may need to add)" -ForegroundColor Yellow
}

Write-Host "`n=== Check Complete ===" -ForegroundColor Cyan
```

## 📚 関連ファイル

- `docker-compose.always-ready-llm.yml` - Open WebUIのDocker設定
- `check_all_services_status.ps1` - サービス状態確認スクリプト
- `x280_verify_connection.ps1` - Tailscale接続確認スクリプト（参考）
