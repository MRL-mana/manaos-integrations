# Open WebUI Tailscale アクセス - 最終セットアップ手順

## ✅ 完了済みの設定

1. **Docker Compose設定** ✅
   - ポートバインディング: `0.0.0.0:3001:8080` に修正済み
   - すべてのネットワークインターフェースでリッスン

2. **Open WebUIコンテナ** ✅
   - 起動中: `open-webui`
   - ポート: `0.0.0.0:3001->8080/tcp`
   - ステータス: HTTP 200 (正常動作)

3. **ポートリッスン** ✅
   - ポート3001は全インターフェースでリッスン中

## ⚠️ 残り1ステップ: ファイアウォールルールの追加

**管理者権限が必要です！**

### 方法1: スクリプトを実行（推奨）

1. **管理者としてPowerShellを開く**
   - Windowsキー → "PowerShell" を検索
   - 右クリック → **"管理者として実行"**

2. **スクリプトを実行**
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   .\add_firewall_rule_admin.ps1
   ```

### 方法2: 直接コマンドを実行

**管理者としてPowerShellを開いて：**

```powershell
New-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" `
    -Direction Inbound `
    -LocalPort 3001 `
    -Protocol TCP `
    -Action Allow `
    -Profile Private,Public
```

## 🎯 ファイアウォールルール追加後の確認

### 1. Tailscale IPの確認

**ホスト側（Open WebUIが動いている端末）で：**

```powershell
# 方法1: PowerShellで確認
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like "100.*"} | Select-Object InterfaceAlias, IPAddress

# 方法2: Tailscaleアプリから確認
# Tailscaleアプリを開いて、自分のデバイスのIPアドレスを確認
```

### 2. リモート端末からのアクセス

Tailscale IPが `100.127.121.20` の場合：

```
http://100.127.121.20:3001
```

### 3. 接続テスト

**リモート端末から：**

```powershell
# ポート接続テスト
Test-NetConnection -ComputerName 100.127.121.20 -Port 3001

# ブラウザでアクセス
# http://100.127.121.20:3001
```

## 📋 完全なチェックリスト

- [x] Docker Compose設定を `0.0.0.0:3001:8080` に修正
- [x] Open WebUIコンテナが起動中
- [x] ポート3001が全インターフェースでリッスン
- [x] Open WebUIが正常に動作（HTTP 200）
- [ ] **ファイアウォールルールを追加（管理者権限が必要）**
- [ ] Tailscale IPを確認
- [ ] リモート端末から接続テスト

## 🔍 トラブルシューティング

### ファイアウォールルールが追加できない

**エラー**: "アクセスが拒否されました"

**解決方法**:
1. PowerShellを**管理者として実行**する
2. ユーザーアカウント制御（UAC）の確認を許可する

### 接続できない場合

#### 1. ファイアウォールルールの確認

```powershell
Get-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" | Format-List *
```

#### 2. ポートの確認

```powershell
# ポート3001がリッスンしているか確認
Get-NetTCPConnection -LocalPort 3001

# Dockerコンテナの状態確認
docker ps --filter "name=open-webui"
```

#### 3. Tailscale接続確認

**両方の端末で：**

```powershell
# Tailscaleのステータス確認
tailscale status

# または
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like "100.*"}
```

## 🚀 クイックスタート

1. **管理者としてPowerShellを開く**
2. **ファイアウォールルールを追加**
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   .\add_firewall_rule_admin.ps1
   ```
3. **Tailscale IPを確認**
   - Tailscaleアプリから確認
4. **リモート端末からアクセス**
   - ブラウザで `http://<Tailscale IP>:3001`

## 📊 現在の状態

- ✅ Open WebUI: 正常動作中
- ✅ ポートバインディング: 正しく設定済み
- ⚠️ ファイアウォール: ルール追加が必要（管理者権限）

## 📚 関連ファイル

- `add_firewall_rule_admin.ps1` - ファイアウォールルール追加スクリプト
- `check_openwebui_tailscale_access.ps1` - 確認スクリプト
- `docker-compose.always-ready-llm.yml` - Docker Compose設定（修正済み）
