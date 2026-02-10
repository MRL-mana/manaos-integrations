$ErrorActionPreference = 'Stop'

# まなOS（Moltbot Gateway）+ OpenClaw Gateway の簡易ヘルスチェック＆自動復旧
# - 8088: moltbot_gateway (uvicorn)
# - 18789: openclaw gateway
# 使い方: リポジトリルートで .\moltbot_gateway\deploy\heal_manaos_services.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
Set-Location $repoRoot

function IsListening([int]$port) {
    $c = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' } | Select-Object -First 1
    return [bool]$c
}

function StartTaskIfExists([string]$taskName) {
    $t = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $t) { return $false }
    try {
        Start-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Out-Null
        return $true
    } catch {
        return $false
    }
}

function KillPortOwner([int]$port) {
    try {
        $pid = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
        if ($pid -and $pid -gt 0) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
    } catch {}
}

# ---- OpenClaw (18789) ----
if (-not (IsListening 18789)) {
    # まず常駐タスクで起動（公式タスクより、repo側の OpenClawGateway を優先）
    $started = StartTaskIfExists 'OpenClawGateway'
    if (-not $started) { $null = StartTaskIfExists 'OpenClaw Gateway' }
    Start-Sleep -Seconds 3
    if (-not (IsListening 18789)) {
        # タスクが死んでる/環境不足の可能性 → repo スクリプトで直接起動
        Start-Process powershell.exe -ArgumentList @(
            '-NoProfile','-ExecutionPolicy','Bypass',
            '-File', (Join-Path $repoRoot 'moltbot_gateway\deploy\run_openclaw_gateway_production.ps1')
        ) -WindowStyle Hidden | Out-Null
        Start-Sleep -Seconds 3
    }
}

# ---- Moltbot Gateway (8088) ----
if (-not (IsListening 8088)) {
    $null = StartTaskIfExists 'MoltbotGateway'
    Start-Sleep -Seconds 3
    if (-not (IsListening 8088)) {
        Start-Process powershell.exe -ArgumentList @(
            '-NoProfile','-ExecutionPolicy','Bypass',
            '-File', (Join-Path $repoRoot 'moltbot_gateway\deploy\run_gateway_wrapper_production.ps1')
        ) -WindowStyle Hidden | Out-Null
        Start-Sleep -Seconds 3
    }
}

# どうしてもゾンビで LISTEN が取れない時用（任意）
if (-not (IsListening 18789)) { KillPortOwner 18789 }
if (-not (IsListening 8088)) { KillPortOwner 8088 }

Write-Host ("OK: 18789={0} 8088={1}" -f (IsListening 18789), (IsListening 8088))
