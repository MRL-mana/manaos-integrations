param(
    [string]$BaseDomain,
    [string]$AdminEmail = "mana-blueprint-admin@example.local",
    [string]$AdminPassword = "ManaOS!2026",
    [switch]$StartIfNeeded
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

function Step($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

function Ok($msg) {
    Write-Host "[OK] $msg" -ForegroundColor Green
}

function Ng($msg) {
    Write-Host "[NG] $msg" -ForegroundColor Red
}

function Get-EnvValue {
    param(
        [string]$EnvPath,
        [string]$Key,
        [string]$Default = ""
    )

    if (-not (Test-Path $EnvPath)) {
        return $Default
    }

    $line = Get-Content $EnvPath | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
    if (-not $line) {
        return $Default
    }

    return ($line -split "=", 2)[1].Trim()
}

function Invoke-JsonRequest {
    param(
        [ValidateSet("GET", "POST", "DELETE")]
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers,
        [object]$Body
    )

    $params = @{
        Method = $Method
        Uri = $Url
        Headers = $Headers
        TimeoutSec = 20
    }

    if ($null -ne $Body) {
        $params["ContentType"] = "application/json"
        $params["Body"] = ($Body | ConvertTo-Json -Depth 10 -Compress)
    }

    return Invoke-RestMethod @params
}

function Get-HttpStatusCode {
    param(
        [string]$Url,
        [string]$HostHeader
    )

    $request = [System.Net.HttpWebRequest]::Create($Url)
    $request.Method = "GET"
    $request.AllowAutoRedirect = $false
    $request.Timeout = 10000
    $request.Host = $HostHeader

    try {
        $response = $request.GetResponse()
        $statusCode = [int]$response.StatusCode
        $response.Close()
        return $statusCode
    }
    catch [System.Net.WebException] {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            $_.Exception.Response.Close()
            return $statusCode
        }
        throw
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$composeFile = Join-Path $scriptDir "docker-compose.blueprint.yml"
$envPath = Join-Path $scriptDir ".env"

if (-not (Test-Path $envPath)) {
    throw ".env not found: $envPath"
}

$resolvedBaseDomain = $BaseDomain
if ([string]::IsNullOrWhiteSpace($resolvedBaseDomain)) {
    $resolvedBaseDomain = Get-EnvValue -EnvPath $envPath -Key "BASE_DOMAIN" -Default "mrl-mana.com"
}

$opsToken = Get-EnvValue -EnvPath $envPath -Key "OPS_EXEC_BEARER_TOKEN" -Default ""

if ($StartIfNeeded) {
    Step "Start blueprint stack"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    docker compose -f $composeFile --env-file $envPath up -d 2>$null | Out-Host
    $ErrorActionPreference = $prevEap
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed (exit=$LASTEXITCODE)"
    }
}

$failures = 0

Step "Ingress health checks"
try {
    $apiCode = Get-HttpStatusCode -Url "http://localhost/health" -HostHeader "api.$resolvedBaseDomain"
    if ($apiCode -eq 200) { Ok "api.$resolvedBaseDomain /health => 200" } else { Ng "api health status=$apiCode"; $failures++ }

    $chatCode = Get-HttpStatusCode -Url "http://localhost/" -HostHeader "chat.$resolvedBaseDomain"
    if ($chatCode -eq 200) { Ok "chat.$resolvedBaseDomain / => 200" } else { Ng "chat status=$chatCode"; $failures++ }

    $codeCode = Get-HttpStatusCode -Url "http://localhost/" -HostHeader "code.$resolvedBaseDomain"
    if ($codeCode -in @(200, 302)) { Ok "code.$resolvedBaseDomain / => $codeCode" } else { Ng "code status=$codeCode"; $failures++ }
}
catch {
    Ng "Ingress checks failed: $($_.Exception.Message)"
    $failures++
}

Step "Blueprint API checks"
try {
    $apiHeaders = @{ Host = "api.$resolvedBaseDomain" }

    $write = Invoke-JsonRequest -Method "POST" -Url "http://localhost/memory/write" -Headers $apiHeaders -Body @{ content = "acceptance memory"; metadata = @{ suite = "blueprint" } }
    if ($write.success -eq $true) { Ok "memory/write" } else { Ng "memory/write failed"; $failures++ }

    $search = Invoke-JsonRequest -Method "POST" -Url "http://localhost/memory/search" -Headers $apiHeaders -Body @{ query = "acceptance"; limit = 5 }
    if ($search.success -eq $true -and $search.count -ge 1) { Ok "memory/search" } else { Ng "memory/search failed"; $failures++ }

    $plan = Invoke-JsonRequest -Method "POST" -Url "http://localhost/ops/plan" -Headers $apiHeaders -Body @{ goal = "acceptance run" }
    if ($plan.success -eq $true -and $plan.plan.plan_id) { Ok "ops/plan" } else { Ng "ops/plan failed"; $failures++ }

    $execHeaders = @{ Host = "api.$resolvedBaseDomain"; Authorization = "Bearer $opsToken" }
    $exec = Invoke-JsonRequest -Method "POST" -Url "http://localhost/ops/exec" -Headers $execHeaders -Body @{ command = "echo acceptance"; approved = $true; dry_run = $true }
    if ($exec.success -eq $true -and $exec.returncode -eq 0) { Ok "ops/exec dry-run" } else { Ng "ops/exec failed"; $failures++ }
}
catch {
    Ng "API checks failed: $($_.Exception.Message)"
    $failures++
}

Step "Open WebUI auth and tool checks"
try {
    $chatHeaders = @{ Host = "chat.$resolvedBaseDomain" }
    $signin = Invoke-JsonRequest -Method "POST" -Url "http://localhost/api/v1/auths/signin" -Headers $chatHeaders -Body @{ email = $AdminEmail; password = $AdminPassword }
    $token = $signin.token
    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "signin token is empty"
    }
    Ok "Open WebUI signin"

    $authHeaders = @{ Host = "chat.$resolvedBaseDomain"; Authorization = "Bearer $token" }
    $tool = Invoke-JsonRequest -Method "GET" -Url "http://localhost/api/v1/tools/id/manaos_blueprint_gateway" -Headers $authHeaders -Body $null

    $requiredSpecs = @("memory_write", "memory_search", "ops_plan", "ops_exec", "dev_patch", "dev_test", "dev_deploy")
    $actualSpecs = @($tool.specs | ForEach-Object { $_.name })
    $missing = @($requiredSpecs | Where-Object { $_ -notin $actualSpecs })

    if ($missing.Count -eq 0) {
        Ok "Open WebUI tool specs complete"
    }
    else {
        Ng ("Missing tool specs: " + ($missing -join ", "))
        $failures++
    }
}
catch {
    Ng "Open WebUI checks failed: $($_.Exception.Message)"
    $failures++
}

Step "Summary"
if ($failures -eq 0) {
    Ok "Blueprint acceptance PASSED"
    exit 0
}

Ng "Blueprint acceptance FAILED (count=$failures)"
exit 1
