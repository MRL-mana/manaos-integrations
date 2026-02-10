# 本物 OpenClaw で Gateway を起動するラッパー
# gateway_production.env があればそれを読み、なければモックのまま起動
# 使い方: リポジトリルートで .\moltbot_gateway\deploy\run_gateway_wrapper_production.ps1

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
Set-Location $repoRoot

$dataDir = Join-Path $repoRoot "moltbot_gateway_data"
$secret = "local_secret"

$env:MOLTBOT_GATEWAY_DATA_DIR = $dataDir
$env:MOLTBOT_GATEWAY_SECRET = $secret

$envFile = Join-Path $scriptDir "gateway_production.env"
if (Test-Path $envFile) {
    Get-Content $envFile -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            $k = $matches[1]; $v = $matches[2].Trim()
            if ($v -match '^["''](.*)["'']\s*$') { $v = $matches[1] }
            Set-Item -Path "env:$k" -Value $v -ErrorAction SilentlyContinue
        }
    }
    Write-Host "Loaded gateway_production.env -> EXECUTOR=$env:EXECUTOR MOLTBOT_DAEMON_URL=$env:MOLTBOT_DAEMON_URL"
} else {
    $env:EXECUTOR = "mock"
    Write-Host "No gateway_production.env -> EXECUTOR=mock"
}

& python -m uvicorn moltbot_gateway.gateway_app:app --host 127.0.0.1 --port 8088
