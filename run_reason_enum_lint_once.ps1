param(
    [string]$ConfigFile = "",
    [string]$RepoRoot = "",
    [switch]$IncludeCheckScripts,
    [string]$LatestJsonFile = "",
    [string]$HistoryJsonl = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = $scriptDir
}
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\reason_enum_lint_task.config.json"
}
if ([string]::IsNullOrWhiteSpace($LatestJsonFile)) {
    $LatestJsonFile = Join-Path $scriptDir "logs\reason_enum_lint.latest.json"
}
if ([string]::IsNullOrWhiteSpace($HistoryJsonl)) {
    $HistoryJsonl = Join-Path $scriptDir "logs\reason_enum_lint.history.jsonl"
}

function To-Bool {
    param(
        [object]$Value,
        [bool]$Default = $false
    )
    if ($null -eq $Value) { return $Default }
    if ($Value -is [bool]) { return [bool]$Value }
    $text = ([string]$Value).Trim().ToLowerInvariant()
    if ($text -in @('1','true','yes','on','enabled')) { return $true }
    if ($text -in @('0','false','no','off','disabled')) { return $false }
    return $Default
}

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.repo_root -and -not $PSBoundParameters.ContainsKey('RepoRoot')) { $RepoRoot = [string]$cfg.repo_root }
        if ($cfg.latest_json_file -and -not $PSBoundParameters.ContainsKey('LatestJsonFile')) { $LatestJsonFile = [string]$cfg.latest_json_file }
        if ($cfg.history_jsonl -and -not $PSBoundParameters.ContainsKey('HistoryJsonl')) { $HistoryJsonl = [string]$cfg.history_jsonl }
        if ($null -ne $cfg.include_check_scripts -and -not $PSBoundParameters.ContainsKey('IncludeCheckScripts')) {
            $IncludeCheckScripts = To-Bool $cfg.include_check_scripts
        }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

$lintScript = Join-Path $RepoRoot "lint_reason_enum.ps1"
if (-not (Test-Path $lintScript)) {
    throw "Lint script not found: $lintScript"
}

$latestDir = Split-Path -Parent $LatestJsonFile
if ($latestDir -and -not (Test-Path $latestDir)) {
    New-Item -ItemType Directory -Path $latestDir -Force | Out-Null
}
$historyDir = Split-Path -Parent $HistoryJsonl
if ($historyDir -and -not (Test-Path $historyDir)) {
    New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
}

$runTs = [datetimeoffset]::Now.ToString('o')
$outputLines = @()
$exitCode = 999
$ok = $false
$okReason = 'lint_error'

try {
    $pwshArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$lintScript)
    if ($IncludeCheckScripts.IsPresent) {
        $pwshArgs += '-IncludeCheckScripts'
    }

    $outputLines = @(& pwsh @pwshArgs 2>&1 | ForEach-Object { [string]$_ })
    $exitCode = $LASTEXITCODE
    $ok = ($exitCode -eq 0)
    $okReason = if ($ok) { 'lint_passed' } else { 'lint_failed' }
}
catch {
    $outputLines = @($_.Exception.Message)
    $exitCode = 999
    $ok = $false
    $okReason = 'lint_error'
}

$outputTail = @($outputLines | Select-Object -Last 20)
$payload = [ordered]@{
    ts = $runTs
    ok = $ok
    ok_reason = $okReason
    include_check_scripts = [bool]$IncludeCheckScripts
    exit_code = [int]$exitCode
    repo_root = $RepoRoot
    lint_script = $lintScript
    config_file = $ConfigFile
    latest_json_file = $LatestJsonFile
    history_jsonl = $HistoryJsonl
    output_tail = $outputTail
}

($payload | ConvertTo-Json -Depth 8) | Set-Content -Path $LatestJsonFile -Encoding UTF8
($payload | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Path $HistoryJsonl -Encoding UTF8

if ($ok) {
    Write-Host "[OK] reason-enum lint passed" -ForegroundColor Green
}
else {
    Write-Host "[ALERT] reason-enum lint failed (exit=$exitCode)" -ForegroundColor Red
}

$outputTail | ForEach-Object { Write-Host $_ }
exit $exitCode
