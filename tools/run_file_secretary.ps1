param(
    [string]$Inbox = "00_INBOX",
    [string]$Rules = "config/file_secretary_rules.yaml",
    [string]$AuditLog = "logs/file_secretary_audit.jsonl"
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

$logDir = Join-Path $repo "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$runLog = Join-Path $logDir "file_secretary_run.log"
$lock = Join-Path $logDir "file_secretary.lock"

$inboxPath = if ([System.IO.Path]::IsPathRooted($Inbox)) {
    $Inbox
} else {
    Join-Path $repo $Inbox
}

$rulesPath = if ([System.IO.Path]::IsPathRooted($Rules)) {
    $Rules
} else {
    Join-Path $repo $Rules
}

$auditPath = if ([System.IO.Path]::IsPathRooted($AuditLog)) {
    $AuditLog
} else {
    Join-Path $repo $AuditLog
}

$pythonExe = $null
$repoParent = Split-Path -Parent $repo
$candidates = @(
    (Join-Path $repoParent ".venv310\Scripts\python.exe"),
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

$now = Get-Date
$ts = $now.ToString("yyyy-MM-dd HH:mm:ss")

Add-Content -Path $runLog -Value "$ts INFO python=$pythonExe inbox=$inboxPath rules=$rulesPath"

if (Test-Path $lock) {
    $age = $now - (Get-Item $lock).LastWriteTime
    if ($age.TotalMinutes -lt 5) {
        Add-Content -Path $runLog -Value "$ts SKIP(lock)"
        exit 0
    }
    Remove-Item $lock -Force
}

New-Item -ItemType File -Force -Path $lock | Out-Null

try {
    if (-not (Test-Path $inboxPath)) {
        throw "inbox not found: $inboxPath"
    }
    if (-not (Test-Path $rulesPath)) {
        throw "rules not found: $rulesPath"
    }

    $output = & $pythonExe "tools/file_secretary_engine.py" --inbox $inboxPath --rules $rulesPath --audit-log $auditPath 2>&1
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        $snippet = ($output | Select-Object -Last 12) -join " | "
        Add-Content -Path $runLog -Value "$ts FAIL(exit=$exitCode) $snippet"
        exit 1
    }

    $tail = ($output | Select-Object -Last 1)
    Add-Content -Path $runLog -Value "$ts OK $tail"
    exit 0
}
catch {
    Add-Content -Path $runLog -Value "$ts FAIL $($_.Exception.Message)"
    exit 1
}
finally {
    if (Test-Path $lock) {
        Remove-Item $lock -Force
    }
}
