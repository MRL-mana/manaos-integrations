param(
    [switch]$RemoveOrphans,
    [switch]$SkipServe,
    [int]$ServeTimeoutSec = 15,
    [string]$WebhookUrl = "",
    [switch]$EnsureStartupTask,
    [string]$StartupTaskName = "ManaOS_OpenWebUI_Tailscale_AutoStart",
    [string]$InvocationSource = "manual"
)
Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray

$ErrorActionPreference = "Stop"

function Write-Step($text) {
    Write-Host "`n== $text ==" -ForegroundColor Cyan
}

function Test-DockerReady {
    try {
        docker version | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Get-TailscaleExe {
    $ts = Join-Path $env:ProgramFiles "Tailscale IPN\tailscale.exe"
    if (Test-Path $ts) {
        return $ts
    }
    return "tailscale"
}

function Invoke-WithRetry {
    param(
        [Parameter(Mandatory = $true)]
        [ScriptBlock]$Action,
        [int]$MaxAttempts = 5,
        [int]$DelaySeconds = 2
    )

    $lastError = $null
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            return & $Action
        }
        catch {
            $lastError = $_
            if ($attempt -lt $MaxAttempts) {
                Start-Sleep -Seconds $DelaySeconds
            }
        }
    }

    throw $lastError
}

function Ensure-FirewallRule {
    $ruleName = "Open WebUI Tailscale Access"
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort 3001 -Action Allow -Profile Private | Out-Null
        Write-Host "[OK] Firewall rule created for port 3001" -ForegroundColor Green
        return
    }

    if ($existing.Enabled -ne "True") {
        Enable-NetFirewallRule -DisplayName $ruleName | Out-Null
    }
    Write-Host "[OK] Firewall rule ready for port 3001" -ForegroundColor Green
}

function Ensure-StartupScheduledTask {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TaskName,
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [int]$TimeoutSec = 20,
        [string]$Source = "startup_task"
    )

    $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
    if (-not (Test-Path $psExe)) {
        $psExe = "powershell.exe"
    }

    $quotedScript = '"' + $ScriptPath + '"'
    $args = "-NoProfile -ExecutionPolicy Bypass -File $quotedScript -ServeTimeoutSec $TimeoutSec -InvocationSource $Source"

    $action = New-ScheduledTaskAction -Execute $psExe -Argument $args
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Auto-start OpenWebUI + Tailscale endpoint" -Force | Out-Null
}

function Ensure-StartupRunEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EntryName,
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [int]$TimeoutSec = 20,
        [string]$Source = "startup_run_key"
    )

    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
    if (-not (Test-Path $psExe)) {
        $psExe = "powershell.exe"
    }

    $cmd = '"' + $psExe + '" -NoProfile -ExecutionPolicy Bypass -File "' + $ScriptPath + '" -ServeTimeoutSec ' + $TimeoutSec + ' -InvocationSource ' + $Source
    if (-not (Test-Path $runKey)) {
        New-Item -Path $runKey -Force | Out-Null
    }
    Set-ItemProperty -Path $runKey -Name $EntryName -Value $cmd -Type String
}

function Get-StartupRegistrationState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TaskName,
        [Parameter(Mandatory = $true)]
        [string]$EntryName
    )

    try {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        if ($task) {
            return [ordered]@{
                mode = "scheduled_task"
                detail = $TaskName
            }
        }
    }
    catch {
    }

    try {
        $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
        $v = (Get-ItemProperty -Path $runKey -Name $EntryName -ErrorAction Stop).$EntryName
        if (-not [string]::IsNullOrWhiteSpace($v)) {
            return [ordered]@{
                mode = "run_key"
                detail = $EntryName
            }
        }
    }
    catch {
    }

    return [ordered]@{
        mode = "none"
        detail = $null
    }
}

Write-Host "Start OpenWebUI + Tailscale setup" -ForegroundColor Green

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot

$startupState = Get-StartupRegistrationState -TaskName $StartupTaskName -EntryName $StartupTaskName
$startupRegistration = $startupState.mode
$startupRegistrationDetail = $startupState.detail

if ($EnsureStartupTask) {
    Write-Step "Ensure Startup Task"
    try {
        Ensure-StartupScheduledTask -TaskName $StartupTaskName -ScriptPath $MyInvocation.MyCommand.Path -TimeoutSec $ServeTimeoutSec -Source "startup_task"
        Write-Host "[OK] Startup task ensured: $StartupTaskName" -ForegroundColor Green
        $startupRegistration = "scheduled_task"
        $startupRegistrationDetail = $StartupTaskName
    }
    catch {
        Write-Host "[WARN] Failed to ensure startup task: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "[INFO] Fallback to HKCU Run entry..." -ForegroundColor Gray
        try {
            Ensure-StartupRunEntry -EntryName $StartupTaskName -ScriptPath $MyInvocation.MyCommand.Path -TimeoutSec $ServeTimeoutSec -Source "startup_run_key"
            Write-Host "[OK] Startup Run entry ensured: $StartupTaskName" -ForegroundColor Green
            $startupRegistration = "run_key"
            $startupRegistrationDetail = $StartupTaskName
        }
        catch {
            Write-Host "[WARN] Failed to ensure Run entry: $($_.Exception.Message)" -ForegroundColor Yellow
            $startupRegistration = "failed"
            $startupRegistrationDetail = $_.Exception.Message
        }
    }
}

$composeFile = Join-Path $scriptRoot "docker-compose.always-ready-llm.yml"
if (-not (Test-Path $composeFile)) {
    throw "Compose file not found: $composeFile"
}

Write-Step "Check Docker"
if (-not (Test-DockerReady)) {
    $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktop) {
        Start-Process $dockerDesktop | Out-Null
    }

    $ready = $false
    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 2
        if (Test-DockerReady) {
            $ready = $true
            break
        }
    }

    if (-not $ready) {
        throw "Docker is not ready. Start Docker Desktop and retry."
    }
}
Write-Host "[OK] Docker ready" -ForegroundColor Green

Write-Step "Start OpenWebUI"
$composeArgs = @("compose", "-f", $composeFile, "up", "-d", "openwebui")
if ($RemoveOrphans) {
    $composeArgs += "--remove-orphans"
}
docker @composeArgs | Out-Null

$httpReady = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 2
    try {
        $status = (Invoke-WebRequest -Uri "http://127.0.0.1:3001/" -UseBasicParsing -TimeoutSec 3).StatusCode
        if ($status -ge 200 -and $status -lt 400) {
            $httpReady = $true
            break
        }
    }
    catch {
    }
}

if (-not $httpReady) {
    throw "OpenWebUI is not responding on port 3001."
}
Write-Host "[OK] OpenWebUI ready on http://127.0.0.1:3001" -ForegroundColor Green

Write-Step "Firewall"
try {
    Ensure-FirewallRule
}
catch {
    Write-Host "[WARN] Firewall rule setup failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Step "Check Tailscale"
$tailscaleExe = Get-TailscaleExe
$tailscaleAvailable = $true
try {
    $null = Get-Command $tailscaleExe -ErrorAction Stop
}
catch {
    $tailscaleAvailable = $false
}

if (-not $tailscaleAvailable) {
    Write-Host "[WARN] Tailscale command not found. Use Local URL only." -ForegroundColor Yellow
    Write-Step "Access URLs"
    Write-Host "Local URL        : http://127.0.0.1:3001" -ForegroundColor White
    Write-Host "Done." -ForegroundColor Green
    exit 0
}

$tsStatus = $null
try {
    $tsStatus = Invoke-WithRetry -MaxAttempts 6 -DelaySeconds 2 -Action {
        $json = & $tailscaleExe status --json
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json)) {
            throw "tailscale status failed"
        }
        return ($json | ConvertFrom-Json)
    }
}
catch {
    Write-Host "[WARN] Failed to query tailscale status. Fallback to interface IP." -ForegroundColor Yellow
}

$selfIp = $null
if ($tsStatus -and $tsStatus.Self.TailscaleIPs -and $tsStatus.Self.TailscaleIPs.Count -gt 0) {
    $selfIp = $tsStatus.Self.TailscaleIPs[0]
}
$selfDns = $null
if ($tsStatus -and $tsStatus.Self.DNSName) {
    $selfDns = $tsStatus.Self.DNSName
}

if (-not $selfIp) {
    $selfIp = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress)
}

if (-not $selfIp) {
    throw "Failed to get Tailscale IP. Check login status."
}
Write-Host "[OK] Tailscale IP: $selfIp" -ForegroundColor Green

Write-Step "Configure Tailscale Serve"
$serveEnabled = $true
$serveError = $null
if ($SkipServe) {
    $serveEnabled = $false
    $serveError = "Serve step skipped by -SkipServe"
}
else {
    $serveStdOut = Join-Path $env:TEMP "tailscale_serve_stdout.txt"
    $serveStdErr = Join-Path $env:TEMP "tailscale_serve_stderr.txt"
    Remove-Item $serveStdOut, $serveStdErr -ErrorAction SilentlyContinue

    $serveProc = Start-Process -FilePath $tailscaleExe -ArgumentList "serve", "--bg", "--https=443", "http://127.0.0.1:3001" -NoNewWindow -PassThru -RedirectStandardOutput $serveStdOut -RedirectStandardError $serveStdErr
    $finished = $serveProc.WaitForExit($ServeTimeoutSec * 1000)

    if (-not $finished) {
        $serveEnabled = $false
        $serveError = "tailscale serve timed out after $ServeTimeoutSec s"
        try { Stop-Process -Id $serveProc.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
    elseif ($serveProc.ExitCode -ne 0) {
        $stdoutTxt = if (Test-Path $serveStdOut) { (Get-Content $serveStdOut -Raw) } else { "" }
        $stderrTxt = if (Test-Path $serveStdErr) { (Get-Content $serveStdErr -Raw) } else { "" }
        $combined = (($stdoutTxt + "`n" + $stderrTxt).Trim())
        if ($combined -match "Serve started and running in the background" -or $combined -match "Available within your tailnet") {
            $serveEnabled = $true
            $serveError = $null
        }
        else {
            $serveEnabled = $false
            $serveError = $combined
        }
    }
}

Write-Step "Access URLs"
Write-Host "Local URL        : http://127.0.0.1:3001" -ForegroundColor White
Write-Host "Tailscale IP URL : http://$selfIp`:3001" -ForegroundColor White
$httpsUrl = $null
if ($selfDns) {
    $dnsNoDot = $selfDns.TrimEnd('.')
    if ($serveEnabled) {
        $httpsUrl = "https://$dnsNoDot"
        Write-Host "Tailscale HTTPS  : $httpsUrl" -ForegroundColor White
    }
    else {
        Write-Host "Tailscale DNS URL: http://$dnsNoDot`:3001" -ForegroundColor White
    }
}

if (-not $serveEnabled) {
    Write-Host "" 
    Write-Host "[WARN] Tailscale Serve is disabled on this tailnet." -ForegroundColor Yellow
    Write-Host "       Mobile access still works via IP/DNS with :3001." -ForegroundColor Yellow
    if ($serveError) {
        Write-Host "       Detail: $serveError" -ForegroundColor DarkYellow
        if ($serveError -match "https://login\.tailscale\.com/f/serve\?node=[^\s]+") {
            Write-Host "       Enable Serve: $($Matches[0])" -ForegroundColor DarkYellow
        }
    }
}

Write-Step "Smoke Tests"
$localStatus = $null
$tsStatusCode = $null
$httpsStatusCode = $null
try {
    $localStatus = (Invoke-WebRequest -Uri "http://127.0.0.1:3001/" -UseBasicParsing -TimeoutSec 4).StatusCode
    Write-Host "[OK] Local HTTP status: $localStatus" -ForegroundColor Green
}
catch {
    Write-Host "[WARN] Local URL check failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

try {
    $tsUrl = "http://$selfIp`:3001/"
    $tsStatusCode = (Invoke-WebRequest -Uri $tsUrl -UseBasicParsing -TimeoutSec 4).StatusCode
    Write-Host "[OK] Tailscale IP HTTP status: $tsStatusCode" -ForegroundColor Green
}
catch {
    Write-Host "[WARN] Tailscale IP URL check failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

if ($httpsUrl) {
    try {
        $httpsStatusCode = (Invoke-WebRequest -Uri "$httpsUrl/" -UseBasicParsing -TimeoutSec 5).StatusCode
        Write-Host "[OK] Tailscale HTTPS status: $httpsStatusCode" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Tailscale HTTPS check failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Step "Write Status File"
$logsDir = Join-Path $scriptRoot "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
$statusPath = Join-Path $logsDir "openwebui_tailscale_status.json"
$statusObj = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    invocation_source = $InvocationSource
    local_url = "http://127.0.0.1:3001"
    tailscale_ip = $selfIp
    tailscale_ip_url = "http://$selfIp`:3001"
    tailscale_dns = if ($selfDns) { $selfDns.TrimEnd('.') } else { $null }
    tailscale_https_url = $httpsUrl
    serve_enabled = $serveEnabled
    serve_error = $serveError
    startup_registration = $startupRegistration
    startup_registration_detail = $startupRegistrationDetail
    checks = [ordered]@{
        local_http_status = $localStatus
        tailscale_ip_http_status = $tsStatusCode
        tailscale_https_status = $httpsStatusCode
    }
    options = [ordered]@{
        ensure_startup_task = [bool]$EnsureStartupTask
        startup_task_name = $StartupTaskName
        remove_orphans = [bool]$RemoveOrphans
        skip_serve = [bool]$SkipServe
        serve_timeout_sec = $ServeTimeoutSec
    }
}
$statusObj | ConvertTo-Json -Depth 8 | Set-Content -Path $statusPath -Encoding UTF8
Write-Host "[OK] Status written: $statusPath" -ForegroundColor Green

Write-Step "Append Status History"
$historyPath = Join-Path $logsDir "openwebui_tailscale_status_history.jsonl"
($statusObj | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Path $historyPath -Encoding UTF8
Write-Host "[OK] History appended: $historyPath" -ForegroundColor Green

Write-Step "Webhook Notify (Optional)"
$effectiveWebhook = $WebhookUrl
if ([string]::IsNullOrWhiteSpace($effectiveWebhook)) {
    $effectiveWebhook = $env:OPENWEBUI_TAILSCALE_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($effectiveWebhook)) {
    $effectiveWebhook = $env:MANAOS_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($effectiveWebhook)) {
    $effectiveWebhook = [Environment]::GetEnvironmentVariable("OPENWEBUI_TAILSCALE_WEBHOOK_URL", "User")
}
if ([string]::IsNullOrWhiteSpace($effectiveWebhook)) {
    $effectiveWebhook = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_URL", "User")
}

if ([string]::IsNullOrWhiteSpace($effectiveWebhook)) {
    Write-Host "[INFO] Webhook not set. Skip notification." -ForegroundColor Gray
}
else {
    try {
        Invoke-RestMethod -Uri $effectiveWebhook -Method Post -ContentType "application/json" -Body ($statusObj | ConvertTo-Json -Depth 8) | Out-Null
        Write-Host "[OK] Webhook notification sent." -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Webhook notification failed: $($_.Exception.Message)" -ForegroundColor Yellow
        if ($_.ErrorDetails -and $null -ne $_.ErrorDetails.Message -and $_.ErrorDetails.Message -match '"code"\s*:\s*10015|Unknown Webhook') {
            Write-Host "[WARN] The configured Discord webhook URL is invalid or deleted (code 10015)." -ForegroundColor Yellow
            Write-Host "[INFO] Update it with set_openwebui_notify_env.ps1 -WebhookUrl <new_url>" -ForegroundColor Gray
        }
    }
}

Write-Host "" 
Write-Host "Done." -ForegroundColor Green
