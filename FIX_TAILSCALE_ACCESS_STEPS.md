# Open WebUI Tailscale アクセス修正手順

## 🔧 問題の原因

`ERR_CONNECTION_REFUSED` エラーが発生する主な原因：

1. **Dockerのポートバインディングがlocalhostのみ**
   - WindowsのDocker Desktopは、デフォルトで`127.0.0.1`にバインドすることがある
   - Tailscaleインターフェースからアクセスできない

2. **ファイアウォールがポート3001をブロック**
   - Windowsファイアウォールでポート3001が許可されていない

## ✅ 修正内容

### 1. Docker Compose設定の修正

`docker-compose.always-ready-llm.yml`を修正しました：

```yaml
# 修正前
ports:
  - 3001:8080

# 修正後
ports:
  - 0.0.0.0:3001:8080
```

これにより、すべてのネットワークインターフェース（Tailscale含む）でリッスンします。

### 2. 修正スクリプトの実行

以下のコマンドで自動修正できます：

```powershell
.\fix_openwebui_tailscale_access.ps1
```

このスクリプトは以下を実行します：
- Open WebUIコンテナの状態確認
- ポートバインディングの確認と修正
- ファイアウォールルールの追加
- 接続テスト

## 🚀 手動修正手順

### ステップ1: Docker Compose設定の適用

```powershell
# コンテナを再起動して新しい設定を適用
docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui
```

### ステップ2: ファイアウォールルールの追加

```powershell
# 管理者権限でPowerShellを実行
New-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" `
    -Direction Inbound `
    -LocalPort 3001 `
    -Protocol TCP `
    -Action Allow `
    -Profile Private,Public
```

### ステップ3: ポートバインディングの確認

```powershell
# ポート3001が0.0.0.0でリッスンしているか確認
Get-NetTCPConnection -LocalPort 3001 | Select-Object LocalAddress, State
```

`LocalAddress`が`0.0.0.0`または`::`であることを確認してください。

### ステップ4: 接続テスト

**ホスト側（Open WebUIが動いている端末）:**
```powershell
# Tailscale IPを確認
$tailscaleIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*").IPAddress
Write-Host "Tailscale IP: $tailscaleIP"
Write-Host "Access URL: http://$tailscaleIP:3001"
```

**リモート端末から:**
```powershell
# 接続テスト
Test-NetConnection -ComputerName 100.127.121.20 -Port 3001
```

## 🔍 トラブルシューティング

### まだ接続できない場合

#### 1. Docker Desktopの再起動

```powershell
# Docker Desktopを再起動
Restart-Service docker
# または Docker Desktopアプリから再起動
```

#### 2. コンテナの完全再作成

```powershell
# コンテナを停止して削除
docker-compose -f docker-compose.always-ready-llm.yml down openwebui

# 再起動
docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui
```

#### 3. ポートバインディングの詳細確認

```powershell
# Dockerコンテナのポートマッピングを確認
docker ps --filter "name=open-webui" --format "table {{.Names}}\t{{.Ports}}"
```

出力例：
```
NAMES        PORTS
open-webui   0.0.0.0:3001->8080/tcp
```

`0.0.0.0:3001`となっていることを確認してください。

#### 4. Tailscale接続の確認

```powershell
# Tailscaleのステータス確認
tailscale status

# または
Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*"
```

#### 5. ファイアウォールルールの確認

```powershell
# ファイアウォールルールの詳細確認
Get-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" | Format-List *
```

## 📝 確認チェックリスト

修正後、以下を確認してください：

- [ ] Docker Compose設定が`0.0.0.0:3001:8080`になっている
- [ ] Open WebUIコンテナが起動している
- [ ] ポート3001が`0.0.0.0`でリッスンしている
- [ ] ファイアウォールルールが追加されている
- [ ] Tailscaleが接続されている
- [ ] ローカルから`http://localhost:3001`にアクセスできる
- [ ] リモートから`http://<Tailscale IP>:3001`にアクセスできる

## 🎯 クイック修正（一括実行）

```powershell
# 1. 修正スクリプトを実行
.\fix_openwebui_tailscale_access.ps1

# 2. 確認スクリプトを実行
.\check_openwebui_tailscale_access.ps1
```

## 📚 関連ファイル

- `docker-compose.always-ready-llm.yml` - Docker Compose設定（修正済み）
- `fix_openwebui_tailscale_access.ps1` - 自動修正スクリプト
- `check_openwebui_tailscale_access.ps1` - 確認スクリプト
