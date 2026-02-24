param(
    [string]$CapabilitiesUrl = "http://127.0.0.1:9502/api/svi/capabilities",
    [switch]$Execute,
    [switch]$DryRun,
    [string]$StatusFile = "",
    [int]$TimeoutSec = 30
)

$ErrorActionPreference = 'Stop'

function Get-Capabilities {
    param([string]$Url)
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
        return ($resp.Content | ConvertFrom-Json)
    } catch {
        throw "Failed to fetch capabilities from ${Url}: $($_.Exception.Message)"
    }
}

function Ensure-Dir {
    param([string]$FilePath)
    $dir = Split-Path -Parent $FilePath
    if (-not (Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    }
}

function Write-Status {
    param(
        [string]$State,
        [hashtable]$Extra
    )

    if (-not $StatusFile) { return }
    try {
        $payload = @{
            updated_at = (Get-Date).ToString('o')
            state = $State
        }
        if ($Extra) {
            foreach ($k in $Extra.Keys) {
                $payload[$k] = $Extra[$k]
            }
        }
        $json = ($payload | ConvertTo-Json -Depth 8)
        Ensure-Dir -FilePath $StatusFile
        Set-Content -Path $StatusFile -Value $json -Encoding UTF8
    } catch {
        # ignore
    }
}

$cap = Get-Capabilities -Url $CapabilitiesUrl
$missing = @()
try {
    $missing = @($cap.model_assets.missing)
} catch {
    $missing = @()
}

if (-not $missing -or $missing.Count -eq 0) {
    Write-Host "[OK] No missing model assets." -ForegroundColor Green
    Write-Status -State 'ok' -Extra @{ missing_count = 0 }
    exit 0
}

Write-Host "Missing assets: $($missing.Count)" -ForegroundColor Yellow
Write-Status -State 'ready' -Extra @{ missing_count = $missing.Count }

# Print commands always
foreach ($m in $missing) {
    $dst = [string]$m.target_path
    $src = [string]$m.url
    $cmd = [string]$m.download_ps
    Write-Host "- $($m.role): $dst" -ForegroundColor Cyan
    Write-Host "  url: $src" -ForegroundColor DarkGray
    if ($cmd) { Write-Host "  ps : $cmd" -ForegroundColor DarkGray }
}

if (-not $Execute -or $DryRun) {
    Write-Host "\n[INFO] Not downloading. Re-run with -Execute to start downloads." -ForegroundColor Gray
    Write-Status -State 'dry_run' -Extra @{ missing = $missing }
    exit 0
}

Write-Status -State 'running' -Extra @{ missing = $missing; current_index = 0; total = $missing.Count }

for ($i = 0; $i -lt $missing.Count; $i++) {
    $m = $missing[$i]
    $dst = [string]$m.target_path
    $src = [string]$m.url
    if (-not $src -or -not $dst) {
        Write-Host "[SKIP] Missing url/target_path" -ForegroundColor DarkYellow
        continue
    }
    if (Test-Path $dst) {
        Write-Host "[OK] Exists: $dst" -ForegroundColor Green
        continue
    }

    Ensure-Dir -FilePath $dst

    Write-Host "\n[DL] $($m.role)" -ForegroundColor Yellow
    Write-Host "     $src" -ForegroundColor DarkGray
    Write-Host "  -> $dst" -ForegroundColor DarkGray

    Write-Status -State 'downloading' -Extra @{ current_index = ($i + 1); total = $missing.Count; role = $m.role; target_path = $dst; url = $src; percent = 0 }

    try {
        # Async BITS download with progress polling
        $job = Start-BitsTransfer -Source $src -Destination $dst -Asynchronous
        $jobId = $null
        if ($job) {
            if ($job.PSObject.Properties.Name -contains 'JobId') { $jobId = $job.JobId }
            elseif ($job.PSObject.Properties.Name -contains 'Id') { $jobId = $job.Id }
        }
        if (-not $jobId) {
            throw 'Start-BitsTransfer returned no job id (JobId/Id was empty).'
        }

        Write-Status -State 'downloading' -Extra @{ current_index = ($i + 1); total = $missing.Count; role = $m.role; target_path = $dst; url = $src; percent = 0; bits_job_id = [string]$jobId }
        while ($true) {
            $job = Get-BitsTransfer -JobId $jobId -ErrorAction SilentlyContinue
            if (-not $job) {
                # If the job vanished, do not assume success. Verify the destination file looks complete.
                if (Test-Path $dst) {
                    try {
                        $len = (Get-Item -LiteralPath $dst).Length
                        if ($len -gt 0) {
                            Write-Host "[WARN] BITS job disappeared but file exists: $dst ($len bytes)" -ForegroundColor DarkYellow
                            break
                        }
                    } catch {}
                }
                throw "BITS job disappeared while downloading and destination file is missing/empty (JobId=$jobId)."
            }

            $jobBytesTotal = 0
            try { $jobBytesTotal = [int64]$job.BytesTotal } catch { $jobBytesTotal = 0 }

            if ($job.JobState -in @('Transferred')) {
                Complete-BitsTransfer -BitsJob $job
                break
            }
            if ($job.JobState -in @('Error','TransientError','Cancelled')) {
                throw "BITS job failed: $($job.JobState) $($job.ErrorDescription)"
            }

            $pct = 0
            if ($jobBytesTotal -gt 0) {
                $pct = [int](($job.BytesTransferred / $jobBytesTotal) * 100)
            }
            Write-Status -State 'downloading' -Extra @{ current_index = ($i + 1); total = $missing.Count; role = $m.role; target_path = $dst; url = $src; percent = $pct; bytes_transferred = $job.BytesTransferred; bytes_total = $job.BytesTotal; bits_job_id = [string]$jobId }
            Start-Sleep -Seconds 2
        }
        Write-Host "[OK] Downloaded: $dst" -ForegroundColor Green
        Write-Status -State 'downloaded' -Extra @{ current_index = ($i + 1); total = $missing.Count; role = $m.role; target_path = $dst; url = $src; percent = 100; bits_job_id = [string]$jobId }
    } catch {
        $details = ''
        try { $details = ($_ | Format-List * -Force | Out-String) } catch { $details = '' }
        Write-Host "[NG] Download failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Status -State 'failed' -Extra @{ current_index = ($i + 1); total = $missing.Count; role = $m.role; target_path = $dst; url = $src; error = $_.Exception.Message; error_details = $details }
        throw
    }
}

Write-Host "\n[OK] All downloads finished. Restart ComfyUI to load new models." -ForegroundColor Green
Write-Status -State 'finished' -Extra @{ missing_count = $missing.Count }
