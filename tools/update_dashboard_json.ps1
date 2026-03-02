$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

$outDir = Join-Path $repo "web\dashboard"
$tmp = Join-Path $outDir "dashboard.json.tmp"
$dst = Join-Path $outDir "dashboard.json"
$logDir = Join-Path $repo "logs"
$log = Join-Path $logDir "dashboard_update.log"
$lock = Join-Path $logDir "dashboard_update.lock"

function Get-NotifySummary {
    param(
        [string]$Path,
        [int]$TailLines = 400,
        [int]$LastItems = 10
    )

    $result = [ordered]@{
        log_exists = $false
        count = 0
        last_status = "none"
        last_entry = $null
        recent = @()
    }

    if (-not (Test-Path $Path)) {
        return [pscustomobject]$result
    }

    $result.log_exists = $true

    $matches = Get-Content -Path $Path -Tail $TailLines | Where-Object { $_ -match "notify=" }
    if (-not $matches -or $matches.Count -eq 0) {
        return [pscustomobject]$result
    }

    $result.count = $matches.Count
    $result.last_entry = $matches[-1]

    $statusMatch = [regex]::Match($matches[-1], "notify=([^\s]+)")
    if ($statusMatch.Success) {
        $result.last_status = $statusMatch.Groups[1].Value
    }

    $result.recent = @($matches | Select-Object -Last $LastItems)
    return [pscustomobject]$result
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$pythonExe = $null
$candidates = @(
    (Join-Path $repo ".venv\Scripts\python.exe"),
    (Join-Path $repo "venv\Scripts\python.exe")
)

foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        $pythonExe = $cmd.Source
    }
}

if (-not $pythonExe) {
    throw "python executable not found (.venv/Scripts/python.exe or PATH)"
}

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

if (Test-Path $lock) {
    $lockAgeSec = ((Get-Date) - (Get-Item $lock).LastWriteTime).TotalSeconds
    if ($lockAgeSec -lt 300) {
        Add-Content -Path $log -Value "$ts SKIP lock_active age_sec=$([int]$lockAgeSec)"
        exit 0
    }
    Remove-Item $lock -Force
}

New-Item -ItemType File -Path $lock -Force | Out-Null

try {
    & $pythonExe "tools/dashboard_cli.py" --check --ci --json --no-color | Out-File -FilePath $tmp -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        throw "dashboard_cli.py exited with code $LASTEXITCODE"
    }

    if (-not (Test-Path $tmp)) {
        throw "temporary json not generated: $tmp"
    }

    $dashboard = Get-Content -Path $tmp -Raw | ConvertFrom-Json
    $notifySummary = [ordered]@{
        generated_at = (Get-Date).ToString("s")
        file_secretary_fail_check = Get-NotifySummary -Path (Join-Path $logDir "file_secretary_fail_check.log")
        dashboard_alert = Get-NotifySummary -Path (Join-Path $logDir "dashboard_alert.log")
    }

    $dashboard | Add-Member -MemberType NoteProperty -Name "notify" -Value $notifySummary -Force
    $dashboard | ConvertTo-Json -Depth 20 | Set-Content -Path $tmp -Encoding utf8

    Move-Item -Force $tmp $dst
    Add-Content -Path $log -Value "$ts OK"
}
catch {
    if (Test-Path $tmp) {
        Remove-Item $tmp -Force
    }
    Add-Content -Path $log -Value "$ts FAIL $($_.Exception.Message)"
    exit 1
}
finally {
    if (Test-Path $lock) {
        Remove-Item $lock -Force
    }
}
