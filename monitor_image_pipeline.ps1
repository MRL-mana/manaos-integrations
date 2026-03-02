param(
    [string]$UnifiedApiUrl = "http://127.0.0.1:9502",
    [string]$ComfyUiUrl = "http://127.0.0.1:8188",
    [switch]$ProbeGenerate,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

function Test-Http {
    param(
        [string]$Url,
        [int]$TimeoutSec = 5,
        [int[]]$AlsoOkStatus = @()
    )

    try {
        $r = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing
        return [pscustomobject]@{
            ok = $true
            status = [int]$r.StatusCode
            error = $null
        }
    }
    catch {
        $statusCode = $null
        try {
            if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
        }
        catch {
            $statusCode = $null
        }

        if ($null -ne $statusCode -and $AlsoOkStatus -contains $statusCode) {
            return [pscustomobject]@{
                ok = $true
                status = $statusCode
                error = $null
            }
        }

        return [pscustomobject]@{
            ok = $false
            status = $statusCode
            error = $_.Exception.Message
        }
    }
}

$unifiedHealth = Test-Http -Url ($UnifiedApiUrl.TrimEnd('/') + '/health')
$unifiedComfyGenerate = Test-Http -Url ($UnifiedApiUrl.TrimEnd('/') + '/api/comfyui/generate') -AlsoOkStatus @(405)
$comfySystemStats = Test-Http -Url ($ComfyUiUrl.TrimEnd('/') + '/system_stats')
$comfyCheckpoints = Test-Http -Url ($ComfyUiUrl.TrimEnd('/') + '/object_info/CheckpointLoaderSimple')

$unifiedGenerateRuntime = [pscustomobject]@{
    tested = $false
    ok = $false
    status = $null
    error = "not_tested"
}

if ($ProbeGenerate.IsPresent) {
    $unifiedGenerateRuntime.tested = $true
    try {
        $probeBody = @{ prompt = "manaos image probe"; width = 64; height = 64; steps = 1 } | ConvertTo-Json
        $resp = Invoke-WebRequest -Uri ($UnifiedApiUrl.TrimEnd('/') + '/api/comfyui/generate') -Method Post -ContentType 'application/json' -Body $probeBody -TimeoutSec 8 -UseBasicParsing
        $unifiedGenerateRuntime.ok = $true
        $unifiedGenerateRuntime.status = [int]$resp.StatusCode
        $unifiedGenerateRuntime.error = $null
    }
    catch {
        $statusCode = $null
        try {
            if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
        }
        catch {
            $statusCode = $null
        }
        $unifiedGenerateRuntime.ok = $false
        $unifiedGenerateRuntime.status = $statusCode
        $unifiedGenerateRuntime.error = $_.Exception.Message
    }
}

$directReady = $comfySystemStats.ok -and $comfyCheckpoints.ok
$unifiedReachable = $unifiedHealth.ok -and $unifiedComfyGenerate.ok
$unifiedReady = $unifiedGenerateRuntime.tested -and $unifiedGenerateRuntime.ok

$recommendation = if ($unifiedReady) {
    "Unified API route is available. Use scripts/generate_image_cli.py (default mode)."
}
elseif ($directReady) {
    "Direct ComfyUI route is available. Use scripts/generate_image_cli.py --direct (or default mode with fallback)."
}
else {
    "Both unified route and direct route are unavailable. Start ComfyUI and check unified API environment."
}

$result = [pscustomobject]@{
    ts = [DateTimeOffset]::Now.ToString('o')
    unified_api = [pscustomobject]@{
        base_url = $UnifiedApiUrl
        health = $unifiedHealth
        comfy_generate_endpoint = $unifiedComfyGenerate
        reachable = $unifiedReachable
        runtime_generate = $unifiedGenerateRuntime
        ready = $unifiedReady
    }
    comfyui = [pscustomobject]@{
        base_url = $ComfyUiUrl
        system_stats = $comfySystemStats
        checkpoint_loader = $comfyCheckpoints
        ready = $directReady
    }
    recommendation = $recommendation
}

if ($Json.IsPresent) {
    $result | ConvertTo-Json -Depth 8
    exit 0
}

Write-Host "=== ManaOS Image Pipeline Health ===" -ForegroundColor Cyan
Write-Host "Unified API: $UnifiedApiUrl" -ForegroundColor Gray
Write-Host ("  /health                 : {0}" -f ($(if ($unifiedHealth.ok) {"OK ($($unifiedHealth.status))"} else {"FAIL - $($unifiedHealth.error)"})))
Write-Host ("  /api/comfyui/generate   : {0}" -f ($(if ($unifiedComfyGenerate.ok) {"OK ($($unifiedComfyGenerate.status))"} else {"FAIL - $($unifiedComfyGenerate.error)"})))
Write-Host "ComfyUI: $ComfyUiUrl" -ForegroundColor Gray
Write-Host ("  /system_stats           : {0}" -f ($(if ($comfySystemStats.ok) {"OK ($($comfySystemStats.status))"} else {"FAIL - $($comfySystemStats.error)"})))
Write-Host ("  /object_info/Checkpoint : {0}" -f ($(if ($comfyCheckpoints.ok) {"OK ($($comfyCheckpoints.status))"} else {"FAIL - $($comfyCheckpoints.error)"})))

if ($unifiedReady) {
    Write-Host "[READY] Unified API image generation available" -ForegroundColor Green
}
elseif ($unifiedReachable -and -not $ProbeGenerate.IsPresent -and $directReady) {
    Write-Host "[PARTIAL] Unified API endpoint reachable (runtime not probed). Direct route is available." -ForegroundColor Yellow
}
elseif ($directReady) {
    Write-Host "[PARTIAL] Direct ComfyUI available (use --direct)" -ForegroundColor Yellow
}
else {
    Write-Host "[DOWN] Image generation unavailable" -ForegroundColor Red
}

Write-Host "Recommendation: $recommendation" -ForegroundColor Yellow
exit 0
