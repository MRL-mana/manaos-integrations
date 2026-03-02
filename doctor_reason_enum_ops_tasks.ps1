param(
    [string]$TasksFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($TasksFile)) {
    $TasksFile = Join-Path $scriptDir ".vscode\tasks.json"
}

if (-not (Test-Path $TasksFile)) {
    throw "tasks file not found: $TasksFile"
}

$text = Get-Content -Path $TasksFile -Raw

$labelMatches = [regex]::Matches($text, '"label"\s*:\s*"([^"]+)"')
$labels = @($labelMatches | ForEach-Object { $_.Groups[1].Value })
$labelSet = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
$duplicateLabels = New-Object System.Collections.Generic.List[string]
foreach ($label in $labels) {
    if (-not $labelSet.Add($label)) {
        $duplicateLabels.Add($label)
    }
}

$dependsOnRefs = New-Object System.Collections.Generic.List[string]
$dependsMatches = [regex]::Matches($text, '"dependsOn"\s*:\s*\[(.*?)\]', [System.Text.RegularExpressions.RegexOptions]::Singleline)
foreach ($m in $dependsMatches) {
    $arrText = $m.Groups[1].Value
    $refMatches = [regex]::Matches($arrText, '"([^"]+)"')
    foreach ($r in $refMatches) {
        $dependsOnRefs.Add($r.Groups[1].Value)
    }
}

$missingDepends = New-Object System.Collections.Generic.List[string]
foreach ($dep in $dependsOnRefs) {
    if (-not $labelSet.Contains($dep)) {
        $missingDepends.Add($dep)
    }
}

$payload = [ordered]@{
    tasks_file = $TasksFile
    total_labels = $labels.Count
    duplicate_label_count = $duplicateLabels.Count
    duplicate_labels = @($duplicateLabels | Select-Object -Unique)
    depends_on_ref_count = $dependsOnRefs.Count
    missing_depends_count = $missingDepends.Count
    missing_depends = @($missingDepends | Select-Object -Unique)
    ok = ($duplicateLabels.Count -eq 0 -and $missingDepends.Count -eq 0)
}

Write-Host "=== Reason Enum Ops Tasks Doctor ===" -ForegroundColor Cyan
Write-Host "tasks_file: $TasksFile" -ForegroundColor Gray
Write-Host "total_labels: $($payload.total_labels)" -ForegroundColor Gray
Write-Host "duplicate_label_count: $($payload.duplicate_label_count)" -ForegroundColor Gray
Write-Host "missing_depends_count: $($payload.missing_depends_count)" -ForegroundColor Gray

if ($payload.duplicate_label_count -gt 0) {
    Write-Host "--- duplicate_labels ---" -ForegroundColor Yellow
    $payload.duplicate_labels | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
}
if ($payload.missing_depends_count -gt 0) {
    Write-Host "--- missing_depends ---" -ForegroundColor Yellow
    $payload.missing_depends | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
}

Write-Output ($payload | ConvertTo-Json -Depth 6)
if ($payload.ok) {
    exit 0
}
exit 1
