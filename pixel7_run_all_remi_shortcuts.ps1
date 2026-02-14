param(
    [string]$Serial = "100.84.2.125:5555",
    [string]$ConfigPath = "manaos_integrations/remi_android_shortcuts.json",
    [string]$WorkDir = "manaos_integrations",
    [string]$OutDir = "manaos_integrations",
    [switch]$IncludePost,
    [switch]$IncludeDangerous,
    [int]$WaitMs = 1400
)

$ErrorActionPreference = "Stop"

function Is-DangerousName([string]$name) {
    $n = $name.ToLowerInvariant()
    return (
        $n -match 'emergency' -or
        $n -match 'stop' -or
        $n -match 'cleanup'
    )
}

function Safe-MatchText([string]$displayName) {
    # UIAutomator dump often encodes emoji as HTML entities; matching on the ASCII part is robust.
    $matchText = ($displayName -replace '^[^A-Za-z0-9]+' , '').Trim()
    if ([string]::IsNullOrWhiteSpace($matchText)) {
        # Fallback: just return original if stripping removed everything
        return $displayName
    }
    return $matchText
}

function Safe-FilePart([string]$text) {
    $t = $text
    $t = $t -replace '[^A-Za-z0-9._-]','_'
    $t = $t -replace '_+','_'
    return $t.Trim('_')
}

if (-not (Test-Path $ConfigPath)) {
    throw "Config not found: $ConfigPath"
}

$json = Get-Content -Raw -Encoding UTF8 $ConfigPath | ConvertFrom-Json

$shortcuts = @()
foreach ($cat in $json.categories) {
    foreach ($sc in $cat.shortcuts) {
        $shortcuts += [pscustomobject]@{
            Category = $cat.name
            Name = [string]$sc.name
            Method = [string]$sc.method
            Url = [string]$sc.url
            ResponseHandling = [string]$sc.responseHandling
            Dangerous = (Is-DangerousName([string]$sc.name))
        }
    }
}

if ($shortcuts.Count -eq 0) {
    throw "No shortcuts found in config."
}

Write-Host ("FOUND_SHORTCUTS={0}" -f $shortcuts.Count)

$runList = $shortcuts
if (-not $IncludePost) {
    $runList = $runList | Where-Object { $_.Method -eq 'GET' }
}
if (-not $IncludeDangerous) {
    $runList = $runList | Where-Object { -not $_.Dangerous }
}

Write-Host "RUN_LIST:"
$runList | ForEach-Object {
    Write-Host ("- {0} | {1} | {2} | dangerous={3}" -f $_.Category, $_.Method, $_.Name, $_.Dangerous)
}

if ($runList.Count -eq 0) {
    Write-Host "Nothing to run with current switches. Use -IncludePost and/or -IncludeDangerous."
    exit 0
}

$runner = Join-Path $WorkDir 'pixel7_run_http_shortcuts_action.ps1'
if (-not (Test-Path $runner)) {
    throw "Runner not found: $runner"
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

foreach ($sc in $runList) {
    $matchText = Safe-MatchText $sc.Name
    $filePart = Safe-FilePart $matchText
    # OutPrefix is treated as a base name; pixel7_run_http_shortcuts_action.ps1 will Join-Path with WorkDir.
    $outPrefix = ("_tmp_all_{0}_{1}" -f $timestamp, $filePart)

    Write-Host ""
    Write-Host ("RUN: {0} {1} ({2})" -f $sc.Method, $sc.Name, $sc.Url)

    powershell -NoProfile -ExecutionPolicy Bypass -File $runner `
        -Serial $Serial `
        -ActionLabelContains $matchText `
        -WorkDir $WorkDir `
        -OutPrefix $outPrefix `
        -WaitMs $WaitMs
}
