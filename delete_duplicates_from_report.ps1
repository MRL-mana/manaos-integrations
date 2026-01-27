# Delete duplicate files listed in a duplicate report JSON (safe delete).
# - Verifies SHA256 matches the report before deleting.
# - Deletes only the "DUPE" (2nd path onward) entries.
#
# Usage (recommended, admin not required for these files):
#   powershell -ExecutionPolicy Bypass -File .\delete_duplicates_from_report.ps1 -ReportPath .\artifacts\duplicate_report_large_ai_20260127_211205.json
#
param(
    [Parameter(Mandatory = $true)]
    [string]$ReportPath
)

$ErrorActionPreference = "Stop"

function Format-GB([long]$bytes) {
    return "{0:N2} GB" -f ($bytes / 1GB)
}

function Choose-KeepPath([string[]]$paths) {
    # Heuristics (goal: free C:, keep on D: when possible)
    # - Prefer D:\ over C:\
    # - Prefer shorter paths (usually the canonical location)
    # - Penalize obvious "nested models folder" duplicates
    $best = $null
    $bestScore = -2147483648

    foreach ($p in $paths) {
        $score = 0

        if ($p -like "D:\*") { $score += 1000 }
        elseif ($p -like "C:\*") { $score += 0 }
        else { $score -= 50 }

        if ($p.ToLower().Contains("\models_ai_data\models\")) { $score -= 200 }
        if ($p.ToLower().Contains("\models\models\")) { $score -= 100 }

        $score -= [int]($p.Length / 5)

        if ($score -gt $bestScore) {
            $best = $p
            $bestScore = $score
        }
    }

    return $best
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Delete duplicates from report" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Report: $ReportPath"
Write-Host ""

if (-not (Test-Path $ReportPath)) {
    Write-Host "[ERROR] Report file not found" -ForegroundColor Red
    exit 1
}

$json = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $json.verified_groups) {
    Write-Host "[ERROR] No verified_groups in report" -ForegroundColor Red
    exit 1
}

$totalDeletedBytes = 0
$deletedCount = 0
$skippedCount = 0
$errors = @()

foreach ($g in $json.verified_groups) {
    $sha = [string]$g.sha256
    $sizeBytes = [long]$g.size_bytes
    $paths = @($g.paths)
    if ($paths.Count -lt 2) { continue }

    $keep = Choose-KeepPath -paths ([string[]]$paths)
    if (-not $keep) { $keep = [string]$paths[0] }
    # If chosen keep is missing, pick first existing one.
    if (-not (Test-Path -LiteralPath $keep)) {
        foreach ($p in $paths) {
            if (Test-Path -LiteralPath ([string]$p)) {
                $keep = [string]$p
                break
            }
        }
    }

    Write-Host "Group sha256=$($sha.Substring(0,16))... size=$(Format-GB $sizeBytes) count=$($paths.Count)" -ForegroundColor Yellow
    Write-Host "  KEEP: $keep"

    if (-not (Test-Path -LiteralPath $keep)) {
        $msg = "KEEP missing: $keep"
        Write-Host "  [ERROR] $msg" -ForegroundColor Red
        $errors += $msg
        continue
    }

    # Verify keep hash matches report (best effort; expensive but safest)
    try {
        $keepHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $keep).Hash.ToLower()
        if ($keepHash -ne $sha.ToLower()) {
            $msg = "KEEP hash mismatch. keep=$keepHash report=$sha"
            Write-Host "  [ERROR] $msg" -ForegroundColor Red
            $errors += $msg
            continue
        }
    } catch {
        $msg = "KEEP hash failed: $($_.Exception.Message)"
        Write-Host "  [ERROR] $msg" -ForegroundColor Red
        $errors += $msg
        continue
    }

    foreach ($p in $paths) {
        $dupe = [string]$p
        if ($dupe -eq $keep) { continue }
        Write-Host "  DUPE: $dupe"

        if (-not (Test-Path -LiteralPath $dupe)) {
            Write-Host "    [SKIP] Not found" -ForegroundColor Gray
            $skippedCount++
            continue
        }

        try {
            $dupeInfo = Get-Item -LiteralPath $dupe -Force
            if ($dupeInfo.Length -ne $sizeBytes) {
                Write-Host "    [SKIP] Size mismatch (file=$($dupeInfo.Length) report=$sizeBytes)" -ForegroundColor Yellow
                $skippedCount++
                continue
            }

            $dupeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dupe).Hash.ToLower()
            if ($dupeHash -ne $sha.ToLower()) {
                Write-Host "    [SKIP] Hash mismatch" -ForegroundColor Yellow
                $skippedCount++
                continue
            }

            # Delete
            Remove-Item -LiteralPath $dupe -Force
            Write-Host "    [OK] Deleted ($(Format-GB $sizeBytes))" -ForegroundColor Green
            $deletedCount++
            $totalDeletedBytes += $sizeBytes
        } catch {
            $msg = "Delete failed: $dupe :: $($_.Exception.Message)"
            Write-Host "    [ERROR] $msg" -ForegroundColor Red
            $errors += $msg
        }
    }

    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Deleted files: $deletedCount"
Write-Host "Skipped files: $skippedCount"
Write-Host "Freed: $(Format-GB $totalDeletedBytes)" -ForegroundColor Green
if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Host "Errors:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
}
Write-Host ""
Write-Host "Done" -ForegroundColor Green
