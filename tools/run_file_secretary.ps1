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

if (Test-Path $lock) {
    $age = $now - (Get-Item $lock).LastWriteTime
    if ($age.TotalMinutes -lt 5) {
        Add-Content -Path $runLog -Value "$ts STATUS=SKIP processed=0 errors=0 skipped=0 duration_ms=0"
        exit 0
    }
    Remove-Item $lock -Force
}

New-Item -ItemType File -Force -Path $lock | Out-Null

try {
    $start = Get-Date
    $processed = 0
    $errors = 0
    $skipped = 0

    if (-not (Test-Path $inboxPath)) {
        throw "inbox not found: $inboxPath"
    }
    if (-not (Test-Path $rulesPath)) {
        throw "rules not found: $rulesPath"
    }

    $output = & $pythonExe "tools/file_secretary_engine.py" --inbox $inboxPath --rules $rulesPath --audit-log $auditPath 2>&1
    $exitCode = $LASTEXITCODE

    foreach ($line in $output) {
        if ($line -match '"processed"\s*:\s*(\d+)') { $processed = [int]$Matches[1] }
        if ($line -match '"errors"\s*:\s*(\d+)') { $errors = [int]$Matches[1] }
        if ($line -match '"skipped"\s*:\s*(\d+)') { $skipped = [int]$Matches[1] }
    }

    $durationMs = [int]((Get-Date) - $start).TotalMilliseconds

    if ($exitCode -ne 0) {
        Add-Content -Path $runLog -Value "$ts STATUS=FAIL processed=$processed errors=$errors skipped=$skipped duration_ms=$durationMs"
        exit 1
    }

    Add-Content -Path $runLog -Value "$ts STATUS=OK processed=$processed errors=$errors skipped=$skipped duration_ms=$durationMs"
    exit 0
}
catch {
    Add-Content -Path $runLog -Value "$ts STATUS=FAIL processed=0 errors=1 skipped=0 duration_ms=0"
    exit 1
}
finally {
    if (Test-Path $lock) {
        Remove-Item $lock -Force
    }
}
