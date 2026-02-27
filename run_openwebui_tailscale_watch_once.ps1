param(
    [string]$TaskName = "ManaOS_OpenWebUI_Tailscale_Watch_5min",
    [string]$BaseUrl = "",
    [string]$LogPath = "",
    [string]$JsonOutFile = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    if (-not [string]::IsNullOrWhiteSpace($env:OPENWEBUI_URL)) {
        $BaseUrl = $env:OPENWEBUI_URL.TrimEnd('/')
    }
    else {
        $BaseUrl = "http://127.0.0.1:3001"
    }
}

if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Join-Path $scriptDir "logs\openwebui_tailscale_watch_task.jsonl"
}

$logDir = Split-Path -Parent $LogPath
if (-not [string]::IsNullOrWhiteSpace($logDir) -and -not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$openwebuiOk = $false
$openwebuiStatusCode = $null
$openwebuiError = $null

try {
    $response = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $openwebuiStatusCode = [int]$response.StatusCode
    $openwebuiOk = ($openwebuiStatusCode -ge 200 -and $openwebuiStatusCode -lt 500)
}
catch {
    $openwebuiError = $_.Exception.Message
}

$tailscaleIp = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" -ErrorAction SilentlyContinue |
    Sort-Object -Property InterfaceMetric, SkipAsSource |
    Select-Object -First 1 -ExpandProperty IPAddress

$portCheck = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
$portListening = ($null -ne $portCheck)

$firewallRules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {
    ($_.DisplayName -like "*3001*") -or
    ($_.DisplayName -like "*Open WebUI*") -or
    ($_.DisplayName -like "*OpenWebUI*")
}
$firewallRuleCount = @($firewallRules).Count

$issues = New-Object System.Collections.Generic.List[string]
if (-not $openwebuiOk) {
    if ([string]::IsNullOrWhiteSpace($openwebuiError)) {
        $issues.Add("OpenWebUI check failed")
    }
    else {
        $issues.Add("OpenWebUI check failed: $openwebuiError")
    }
}
if ([string]::IsNullOrWhiteSpace($tailscaleIp)) {
    $issues.Add("Tailscale IP not found")
}
if (-not $portListening) {
    $issues.Add("Port 3001 is not listening")
}

$ok = ($issues.Count -eq 0)

$payload = [ordered]@{
    ts = [datetimeoffset]::Now.ToString("o")
    task = $TaskName
    base_url = $BaseUrl
    ok = $ok
    openwebui_ok = $openwebuiOk
    openwebui_status_code = $openwebuiStatusCode
    tailscale_ip = $tailscaleIp
    port_3001_listening = $portListening
    firewall_rule_count = $firewallRuleCount
    issues = @($issues)
}

$line = $payload | ConvertTo-Json -Compress -Depth 6
Add-Content -Path $LogPath -Value $line -Encoding UTF8

if (-not [string]::IsNullOrWhiteSpace($JsonOutFile)) {
    $jsonDir = Split-Path -Parent $JsonOutFile
    if (-not [string]::IsNullOrWhiteSpace($jsonDir) -and -not (Test-Path $jsonDir)) {
        New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
    }
    ($payload | ConvertTo-Json -Depth 6) | Set-Content -Path $JsonOutFile -Encoding UTF8
}

if ($ok) {
    $msg = "[OK] OpenWebUI/Tailscale watch healthy"
    if ($openwebuiStatusCode) { $msg += " | status=$openwebuiStatusCode" }
    if ($tailscaleIp) { $msg += " | ip=$tailscaleIp" }
    Write-Host $msg -ForegroundColor Green
    exit 0
}

Write-Host "[ALERT] OpenWebUI/Tailscale watch issues detected" -ForegroundColor Red
foreach ($issue in $issues) {
    Write-Host " - $issue" -ForegroundColor Red
}
exit 1
