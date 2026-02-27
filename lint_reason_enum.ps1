param(
    [string]$RepoRoot = "",
    [string]$ReasonDoc = "",
    [switch]$IncludeCheckScripts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

if ([string]::IsNullOrWhiteSpace($ReasonDoc)) {
    $ReasonDoc = Join-Path $RepoRoot "REASON_ENUM.md"
}

if (-not (Test-Path $ReasonDoc)) {
    throw "Reason enum doc not found: $ReasonDoc"
}

$docContent = Get-Content -Path $ReasonDoc -Raw
$allowedReasons = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

$reasonMatches = [regex]::Matches($docContent, '`([a-z_]+)`')
foreach ($match in $reasonMatches) {
    $value = [string]$match.Groups[1].Value
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        [void]$allowedReasons.Add($value)
    }
}

if ($allowedReasons.Count -eq 0) {
    throw "No reason enums found in: $ReasonDoc"
}

$patterns = @('status_*.ps1')
if ($IncludeCheckScripts.IsPresent) {
    $patterns += 'check_*quick*.ps1'
}

$files = New-Object System.Collections.Generic.List[string]
foreach ($pattern in $patterns) {
    Get-ChildItem -Path $RepoRoot -Filter $pattern -File | ForEach-Object {
        $files.Add($_.FullName)
    }
}

$reasonRegex = [regex]'(latest_ok_reason|status_latest_ok_reason|ok_reason)\s*[:=]\s*[''\"]([a-z_]+)[''\"]'
$violations = New-Object System.Collections.Generic.List[object]

foreach ($file in $files) {
    $lineNo = 0
    Get-Content -Path $file | ForEach-Object {
        $lineNo++
        $line = [string]$_
        $m = $reasonRegex.Match($line)
        if ($m.Success) {
            $reason = [string]$m.Groups[2].Value
            if (-not $allowedReasons.Contains($reason)) {
                $violations.Add([pscustomobject]@{
                    file = [System.IO.Path]::GetFileName($file)
                    line = $lineNo
                    key = [string]$m.Groups[1].Value
                    reason = $reason
                    source = $line.Trim()
                })
            }
        }
    }
}

if ($violations.Count -gt 0) {
    Write-Host "[NG] Undefined reason enums detected" -ForegroundColor Red
    $violations | Sort-Object file, line | ForEach-Object {
        Write-Host ("{0}:{1} [{2}] {3}" -f $_.file, $_.line, $_.key, $_.reason) -ForegroundColor Red
    }
    exit 1
}

Write-Host "[OK] Reason enums are consistent with REASON_ENUM.md" -ForegroundColor Green
Write-Host ("Scanned files: {0}" -f $files.Count) -ForegroundColor Gray
Write-Host ("Allowed enums: {0}" -f $allowedReasons.Count) -ForegroundColor Gray
exit 0
