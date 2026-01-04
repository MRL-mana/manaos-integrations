# このはサーバーからGoogle Drive認証情報をコピーするスクリプト

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "このはサーバーからGoogle Drive認証情報をコピー" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

$localCredentialsPath = Join-Path $PSScriptRoot "credentials.json"
$localTokenPath = Join-Path $PSScriptRoot "token.json"

# このはサーバーへの接続確認
Write-Host "[1] このはサーバーへの接続確認..." -ForegroundColor Yellow

# 接続方法を確認
$connectionMethods = @(
    @{Name="直接SSH"; Command="ssh konoha 'echo test'"},
    @{Name="X280経由"; Command="ssh konoha-via-x280 'echo test'"},
    @{Name="Tailscale IP"; Command="ssh root@100.93.120.33 'echo test'"}
)

$connected = $false
$connectionMethod = $null

foreach ($method in $connectionMethods) {
    Write-Host "   $($method.Name)を試行中..." -ForegroundColor Gray
    try {
        $result = Invoke-Expression $method.Command 2>&1
        if ($LASTEXITCODE -eq 0 -or $result -match "test") {
            $connected = $true
            $connectionMethod = $method
            Write-Host "   [OK] $($method.Name)で接続成功" -ForegroundColor Green
            break
        }
    } catch {
        # 接続失敗は無視
    }
}

if (-not $connected) {
    Write-Host "   [NG] このはサーバーに接続できません" -ForegroundColor Red
    Write-Host ""
    Write-Host "接続方法:" -ForegroundColor Yellow
    Write-Host "  1. SSHサービスを復旧（このはサーバー側）" -ForegroundColor Cyan
    Write-Host "  2. または、このはサーバーの画面共有（VNC等）経由でファイルをコピー" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "認証情報ファイルの場所（このはサーバー側）:" -ForegroundColor Yellow
    Write-Host "  /root/credentials.json" -ForegroundColor Gray
    Write-Host "  /root/token.json" -ForegroundColor Gray
    Write-Host "  または" -ForegroundColor Gray
    Write-Host "  /root/.mana_vault/credentials.json" -ForegroundColor Gray
    Write-Host "  /root/.mana_vault/token.json" -ForegroundColor Gray
    Write-Host ""
    Write-Host "手動でコピーする場合:" -ForegroundColor Yellow
    Write-Host "  1. このはサーバーに接続" -ForegroundColor Cyan
    Write-Host "  2. 認証情報ファイルを確認" -ForegroundColor Cyan
    Write-Host "  3. ファイルをダウンロードまたはコピー" -ForegroundColor Cyan
    Write-Host "  4. 母艦の以下の場所に配置:" -ForegroundColor Cyan
    Write-Host "     $localCredentialsPath" -ForegroundColor Gray
    Write-Host "     $localTokenPath" -ForegroundColor Gray
    exit 1
}

# 認証情報ファイルの場所を確認（このはサーバー側）
Write-Host ""
Write-Host "[2] このはサーバー側の認証情報ファイルを検索..." -ForegroundColor Yellow

$remotePaths = @(
    "/root/credentials.json",
    "/root/token.json",
    "/root/.mana_vault/credentials.json",
    "/root/.mana_vault/token.json",
    "/root/manaos_integrations/credentials.json",
    "/root/manaos_integrations/token.json"
)

$foundCredentials = $null
$foundToken = $null

foreach ($path in $remotePaths) {
    if ($path -match "credentials") {
        $checkCommand = "$($connectionMethod.Command -replace 'echo test', "test -f $path && echo 'exists'")"
        try {
            $result = Invoke-Expression $checkCommand 2>&1
            if ($result -match "exists") {
                $foundCredentials = $path
                Write-Host "   [OK] credentials.jsonが見つかりました: $path" -ForegroundColor Green
                break
            }
        } catch {
            # ファイルが見つからない場合は無視
        }
    }
}

foreach ($path in $remotePaths) {
    if ($path -match "token") {
        $checkCommand = "$($connectionMethod.Command -replace 'echo test', "test -f $path && echo 'exists'")"
        try {
            $result = Invoke-Expression $checkCommand 2>&1
            if ($result -match "exists") {
                $foundToken = $path
                Write-Host "   [OK] token.jsonが見つかりました: $path" -ForegroundColor Green
                break
            }
        } catch {
            # ファイルが見つからない場合は無視
        }
    }
}

if (-not $foundCredentials -and -not $foundToken) {
    Write-Host "   [NG] 認証情報ファイルが見つかりませんでした" -ForegroundColor Red
    Write-Host ""
    Write-Host "このはサーバー側で認証情報ファイルを確認してください:" -ForegroundColor Yellow
    Write-Host "  ssh $($connectionMethod.Name -replace ' ', '') 'find /root -name \"credentials.json\" -o -name \"token.json\" 2>/dev/null'" -ForegroundColor Cyan
    exit 1
}

# ファイルをコピー
Write-Host ""
Write-Host "[3] 認証情報ファイルをコピー中..." -ForegroundColor Yellow

if ($foundCredentials) {
    Write-Host "   credentials.jsonをコピー中..." -ForegroundColor Gray
    $copyCommand = "scp $($connectionMethod.Command -replace 'echo test', '' -replace 'ssh ', '')$foundCredentials $localCredentialsPath"
    try {
        Invoke-Expression $copyCommand
        if (Test-Path $localCredentialsPath) {
            Write-Host "   [OK] credentials.jsonをコピーしました" -ForegroundColor Green
        } else {
            Write-Host "   [NG] コピーに失敗しました" -ForegroundColor Red
        }
    } catch {
        Write-Host "   [NG] コピーエラー: $_" -ForegroundColor Red
        Write-Host "   手動でコピーしてください:" -ForegroundColor Yellow
        Write-Host "   scp $($connectionMethod.Name -replace ' ', '')$foundCredentials $localCredentialsPath" -ForegroundColor Cyan
    }
}

if ($foundToken) {
    Write-Host "   token.jsonをコピー中..." -ForegroundColor Gray
    $copyCommand = "scp $($connectionMethod.Command -replace 'echo test', '' -replace 'ssh ', '')$foundToken $localTokenPath"
    try {
        Invoke-Expression $copyCommand
        if (Test-Path $localTokenPath) {
            Write-Host "   [OK] token.jsonをコピーしました" -ForegroundColor Green
        } else {
            Write-Host "   [NG] コピーに失敗しました" -ForegroundColor Red
        }
    } catch {
        Write-Host "   [NG] コピーエラー: $_" -ForegroundColor Red
        Write-Host "   手動でコピーしてください:" -ForegroundColor Yellow
        Write-Host "   scp $($connectionMethod.Name -replace ' ', '')$foundToken $localTokenPath" -ForegroundColor Cyan
    }
}

# 動作確認
Write-Host ""
Write-Host "[4] 動作確認..." -ForegroundColor Yellow

if ((Test-Path $localCredentialsPath) -or (Test-Path $localTokenPath)) {
    Write-Host "   [OK] 認証情報ファイルが配置されました" -ForegroundColor Green
    Write-Host ""
    Write-Host "次のステップ:" -ForegroundColor Cyan
    Write-Host "  認証情報を確認:" -ForegroundColor Yellow
    Write-Host "    .\check_google_drive_setup.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Google Drive統合の動作確認:" -ForegroundColor Yellow
    Write-Host '    python -c "from google_drive_integration import GoogleDriveIntegration; gd = GoogleDriveIntegration(); print(''利用可能'' if gd.is_available() else ''利用不可'')"' -ForegroundColor Gray
} else {
    Write-Host "   [NG] 認証情報ファイルが配置されていません" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "完了" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan

