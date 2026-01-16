# Docker Desktop トラブルシューティングガイド

## 🔍 現在のエラー状況

以下のエラーが発生しています：

1. **`connect ENOENT \\.\pipe\dockerDesktopEngine`**
   - Dockerエンジンが起動していない、またはパイプが見つからない
   
2. **`Failed to fetch extensions`**
   - Docker拡張機能の取得に失敗
   
3. **`Failed to apply settings`**
   - Docker設定の適用に失敗
   
4. **`An unexpected error occurred. Restart Docker Desktop.`**
   - 予期しないエラーが発生

## 🚀 解決手順

### ステップ1: Docker Desktopの完全再起動

#### 方法A: PowerShellから実行（推奨）

```powershell
# 1. Docker Desktopプロセスをすべて終了
Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. 関連プロセスも終了
Get-Process | Where-Object {$_.ProcessName -like "*docker*"} | Stop-Process -Force -ErrorAction SilentlyContinue

# 3. 数秒待機
Start-Sleep -Seconds 5

# 4. Docker Desktopを起動
Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"

# 5. Dockerエンジンの起動を待機（最大60秒）
$maxWait = 60
$waited = 0
$dockerReady = $false

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 2
    $waited += 2
    
    try {
        docker ps 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            Write-Host "✅ Dockerエンジンが起動しました！" -ForegroundColor Green
            break
        }
    } catch {
        # 接続エラーは無視
    }
    
    Write-Host "." -NoNewline
}

if (-not $dockerReady) {
    Write-Host "`n⚠️  Dockerエンジンの起動に時間がかかっています" -ForegroundColor Yellow
}
```

#### 方法B: タスクマネージャーから実行

1. `Ctrl + Shift + Esc` でタスクマネージャーを開く
2. 「Docker Desktop」プロセスをすべて終了
3. 「docker」で始まるプロセスも終了
4. Docker Desktopを再起動

### ステップ2: WSL2の確認と更新

Docker DesktopはWSL2を使用している場合があります：

```powershell
# WSL2の状態を確認
wsl --status

# WSL2を更新
wsl --update

# WSL2ディストリビューションを再起動
wsl --shutdown
```

### ステップ3: Docker Desktopの設定をリセット

Docker Desktopの設定が破損している可能性があります：

1. Docker Desktopを完全に終了
2. 設定ファイルの場所を確認：
   ```powershell
   # 設定ディレクトリ
   $env:APPDATA\Docker
   $env:LOCALAPPDATA\Docker
   ```
3. 必要に応じて設定をバックアップして削除（**注意**: コンテナやイメージの設定も削除されます）

### ステップ4: Windowsの再起動

上記の方法で解決しない場合：

1. すべてのアプリケーションを閉じる
2. Windowsを再起動
3. Docker Desktopを起動

### ステップ5: Docker Desktopの再インストール

最終手段として、Docker Desktopを再インストール：

1. Docker Desktopをアンインストール
2. 残存ファイルを削除：
   ```powershell
   # 設定ディレクトリを削除（バックアップ推奨）
   Remove-Item -Recurse -Force "$env:APPDATA\Docker" -ErrorAction SilentlyContinue
   Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Docker" -ErrorAction SilentlyContinue
   ```
3. Docker Desktopを再インストール: https://www.docker.com/products/docker-desktop

## 🔧 診断コマンド

### Docker CLIの確認

```powershell
# Dockerバージョン確認
docker --version

# Dockerエンジンの状態確認
docker info

# コンテナ一覧（接続できている場合）
docker ps -a

# イメージ一覧
docker images
```

### プロセスの確認

```powershell
# Docker Desktopプロセスの確認
Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue

# すべてのdocker関連プロセス
Get-Process | Where-Object {$_.ProcessName -like "*docker*"}
```

### パイプの確認

```powershell
# Dockerパイプの存在確認
Test-Path "\\.\pipe\dockerDesktopEngine"
Test-Path "\\.\pipe\dockerDesktopLinuxEngine"
```

## 📋 よくある問題と解決法

### 問題1: パイプが見つからない

**原因**: Dockerエンジンが起動していない

**解決法**:
1. Docker Desktopを完全に再起動
2. WSL2を再起動（WSL2を使用している場合）
3. Windowsを再起動

### 問題2: 拡張機能の取得に失敗

**原因**: ネットワーク接続の問題、またはDockerサービスの不調

**解決法**:
1. インターネット接続を確認
2. Docker Desktopを再起動
3. プロキシ設定を確認（企業ネットワークの場合）

### 問題3: 設定の適用に失敗

**原因**: 設定ファイルの破損、または権限の問題

**解決法**:
1. Docker Desktopを管理者権限で実行
2. 設定をリセット
3. 設定ディレクトリの権限を確認

## 💡 予防策

1. **定期的な再起動**: Docker Desktopを定期的に再起動
2. **リソース監視**: メモリやCPUの使用率を監視
3. **ログ確認**: Docker Desktopのログを定期的に確認
4. **更新**: Docker Desktopを最新版に保つ

## 📞 追加のヘルプ

- Docker Desktop公式ドキュメント: https://docs.docker.com/desktop/
- Docker Desktopトラブルシューティング: https://docs.docker.com/desktop/troubleshoot/
- Dockerコミュニティフォーラム: https://forums.docker.com/

## 🔄 クイック修復スクリプト

以下のコマンドを実行すると、自動的に診断と修復を試みます：

```powershell
# Docker Desktopを再起動
Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 5
Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"

# 60秒待機して接続確認
$waited = 0
while ($waited -lt 60) {
    Start-Sleep -Seconds 2
    $waited += 2
    docker ps 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dockerエンジンが起動しました！" -ForegroundColor Green
        break
    }
    Write-Host "." -NoNewline
}
```
