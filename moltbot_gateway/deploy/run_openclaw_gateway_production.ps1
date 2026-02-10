$ErrorActionPreference = "Stop"

# OpenClaw Gateway を production 設定で起動する（フォアグラウンド）
# - token/port は moltbot_gateway\deploy\gateway_production.env から読む
# - 使い方: リポジトリルートで .\moltbot_gateway\deploy\run_openclaw_gateway_production.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
Set-Location $repoRoot

$envFile = Join-Path $scriptDir "gateway_production.env"
if (-not (Test-Path $envFile)) {
    Write-Host "Error: gateway_production.env not found. Create it from gateway_production.env.example first."
    exit 1
}

# env ファイルを読み込む（KEY=VALUE）
Get-Content $envFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        $k = $matches[1]; $v = $matches[2].Trim()
        if ($v -match '^["''](.*)["'']\s*$') { $v = $matches[1] }
        Set-Item -Path "env:$k" -Value $v -ErrorAction SilentlyContinue
    }
}

$url = ($env:MOLTBOT_DAEMON_URL)
if (-not $url) { $url = "" }
$url = $url.Trim()

$token = $env:MOLTBOT_DAEMON_TOKEN
if (-not $token) { $token = $env:OPENCLAW_GATEWAY_TOKEN }
if (-not $token) { $token = "" }
$token = $token.Trim()

if (-not $url) {
    Write-Host "Error: MOLTBOT_DAEMON_URL is empty in gateway_production.env"
    exit 1
}
if (-not $token) {
    Write-Host "Error: MOLTBOT_DAEMON_TOKEN is empty in gateway_production.env"
    exit 1
}

try {
    $uri = [Uri]$url
} catch {
    Write-Host "Error: MOLTBOT_DAEMON_URL is not a valid URL: $url"
    exit 1
}

$port = $uri.Port
if (-not $port -or $port -le 0) { $port = 18789 }

# openclaw コマンド解決（タスク実行では PATH が薄いことがあるためフォールバック）
$openclaw = $null
$cmd = Get-Command openclaw -ErrorAction SilentlyContinue
if ($cmd) {
    $openclaw = $cmd.Path
} else {
    $candidate = Join-Path $env:APPDATA "npm\\openclaw.cmd"
    if (Test-Path $candidate) {
        $openclaw = $candidate
    }
}
if (-not $openclaw) {
    Write-Host "Error: 'openclaw' command not found."
    Write-Host "Hint: Install OpenClaw and ensure npm global bin is in PATH (or %APPDATA%\\npm\\openclaw.cmd exists)."
    Write-Host "See deploy/RUNBOOK_OPENCLAW_PRODUCTION.md"
    exit 1
}

Write-Host "Starting OpenClaw Gateway on 127.0.0.1:$port ..."
Write-Host "Using token from gateway_production.env (Bearer)."
Write-Host "Command: $openclaw gateway run --port $port --bind loopback --auth token --token <redacted>"

& $openclaw gateway run --port $port --bind loopback --auth token --token $token
