$ErrorActionPreference = "Stop"

# スケジューラーのセッション0では $PSScriptRoot が空になる場合があるため、フォールバックを用意
$scriptDir = if ($PSScriptRoot) {
    $PSScriptRoot
} elseif ($PSCommandPath) {
    Split-Path $PSCommandPath -Parent
} elseif ($MyInvocation.MyCommand.Path) {
    Split-Path $MyInvocation.MyCommand.Path -Parent
} else {
    "C:\Users\mana4\Desktop\manaos_integrations\tools"
}
$repo = Split-Path $scriptDir -Parent
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

    $matchedLines = Get-Content -Path $Path -Tail $TailLines | Where-Object { $_ -match "notify=" }
    if (-not $matchedLines -or $matchedLines.Count -eq 0) {
        return [pscustomobject]$result
    }

    $result.count = $matchedLines.Count
    $result.last_entry = $matchedLines[-1]

    $statusMatch = [regex]::Match($matchedLines[-1], "notify=([^\s]+)")
    if ($statusMatch.Success) {
        $result.last_status = $statusMatch.Groups[1].Value
    }

    $result.recent = @($matchedLines | Select-Object -Last $LastItems)
    return [pscustomobject]$result
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$pythonExe = $null
$candidates = @(
    "C:\Users\mana4\Desktop\.venv\Scripts\python.exe",
    (Join-Path $repo ".venv\Scripts\python.exe"),
    (Join-Path $repo "venv\Scripts\python.exe"),
    "C:\Users\mana4\Desktop\.venv310\Scripts\python.exe",
    "C:\Users\mana4\AppData\Local\Programs\Python\Python312\python.exe",
    "C:\Users\mana4\AppData\Local\Programs\Python\Python311\python.exe",
    "C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe"
)

foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    throw "python executable not found"
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

# タイムアウト上限: 120 秒
$TimeoutMs = 120000
$stderrLog = Join-Path $logDir "dashboard_cli_stderr.log"

try {
    # System.Diagnostics.Process + --output で直接ファイル書き込みすることで:
    # 1. Start-Process -RedirectStandardOutput のストリーム仲介ハング問題を回避
    # 2. スケジューラー(セッション0)でのCtrl+Cシグナル伝播を防ぐ (CreateNoWindow)
    # 3. ExitCode が null になるPowerShell既知の問題を回避
    $psi = [System.Diagnostics.ProcessStartInfo]::new([string]$pythonExe)
    $psi.Arguments = "tools/dashboard_cli.py --ci --json --no-color --output `"$tmp`""
    $psi.WorkingDirectory = [string]$repo
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $false
    $psi.RedirectStandardError = $false

    $proc = [System.Diagnostics.Process]::new()
    $proc.StartInfo = $psi
    [void]$proc.Start()

    $finished = $proc.WaitForExit($TimeoutMs)
    if (-not $finished) {
        $proc.Kill()
        [void]$proc.WaitForExit()
        throw "dashboard_cli.py timed out after $($TimeoutMs / 1000)s"
    }

    $exitCode = $proc.ExitCode
    if ($exitCode -ne 0) {
        $stderrContent = if (Test-Path $stderrLog) { Get-Content $stderrLog -Raw -ErrorAction SilentlyContinue } else { "(no stderr)" }
        throw "dashboard_cli.py exited with code $exitCode"
    }

    if (-not (Test-Path $tmp)) {
        throw "temporary json not generated: $tmp"
    }

    $dashboard = Get-Content -Path $tmp -Raw | ConvertFrom-Json
    $notifySummary = [ordered]@{
        generated_at              = (Get-Date).ToString("s")
        file_secretary_fail_check = Get-NotifySummary -Path (Join-Path $logDir "file_secretary_fail_check.log")
        dashboard_alert           = Get-NotifySummary -Path (Join-Path $logDir "dashboard_alert.log")
    }

    $dashboard | Add-Member -MemberType NoteProperty -Name "notify" -Value $notifySummary -Force
    # $dashboard | ConvertTo-Json だとパイプライン経由の型変換エラーが出るため -InputObject を使用
    ConvertTo-Json -InputObject $dashboard -Depth 20 | Set-Content -Path $tmp -Encoding utf8

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