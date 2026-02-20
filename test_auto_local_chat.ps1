param(
    [string]$BaseUrl = "http://127.0.0.1:5211/v1",
    [string]$Model = "auto-local",
    [int]$MaxRetries = 5,
    [int]$RetryDelaySeconds = 3,
    [int]$RequestTimeoutSec = 120,
    [int]$WarmupTimeoutSec = 45,
    [switch]$AutoStartRouter = $true
)

$ErrorActionPreference = "Stop"

$body = @{
    model = $Model
    messages = @(
        @{ role = "system"; content = "You are a concise coding assistant." },
        @{ role = "user"; content = "Return only one Python line: def sum_numbers(nums): return sum(nums)" }
    )
    temperature = 0
    max_tokens = 48
} | ConvertTo-Json -Depth 8

function Start-RouterIfNeeded {
    param([string]$ScriptRoot)

    $startScript = Join-Path $ScriptRoot "start_manaos_llm_openai_router.ps1"
    if (-not (Test-Path $startScript)) {
        return
    }

    Write-Host "router_autostart=begin"
    powershell -NoProfile -ExecutionPolicy Bypass -File $startScript -LlmServer ollama -Port 5211 -AutoSelectPort
    Write-Host "router_autostart=done exit=$LASTEXITCODE"
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($AutoStartRouter) {
    Start-RouterIfNeeded -ScriptRoot $scriptRoot
}

$warmupDeadline = (Get-Date).AddSeconds($WarmupTimeoutSec)
$warmupOk = $false
while ((Get-Date) -lt $warmupDeadline) {
    try {
        $null = Invoke-RestMethod -Uri "$BaseUrl/models" -Method Get -TimeoutSec 10
        $warmupOk = $true
        break
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $warmupOk) {
    throw "router warmup failed. base_url=$BaseUrl timeout=${WarmupTimeoutSec}s"
}

$response = $null
$lastErrorMessage = $null
for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec $RequestTimeoutSec
        break
    }
    catch {
        $lastErrorMessage = $_.Exception.Message
        if ($attempt -lt $MaxRetries) {
            Write-Host "retry=$attempt/$MaxRetries waiting=${RetryDelaySeconds}s reason=$lastErrorMessage"
            Start-Sleep -Seconds $RetryDelaySeconds
            continue
        }
    }
}

if (-not $response) {
    if ($Model -eq "auto-local") {
        Write-Host "[WARN] auto-local timed out, trying explicit fallback model..."
        $fallbackBody = @{
            model = "llama3-uncensored:latest"
            messages = @(
                @{ role = "system"; content = "You are a concise coding assistant." },
                @{ role = "user"; content = "Return: OK" }
            )
            temperature = 0.0
            max_tokens = 16
        } | ConvertTo-Json -Depth 8

        try {
            $response = Invoke-RestMethod -Uri "$BaseUrl/chat/completions" -Method Post -ContentType "application/json" -Body $fallbackBody -TimeoutSec 120
            Write-Host "[WARN] auto-local timeout recovered by explicit model fallback"
        }
        catch {
            throw "auto-local chat test failed after $MaxRetries attempts. base_url=$BaseUrl error=$lastErrorMessage"
        }
    }
    else {
        throw "chat test failed after $MaxRetries attempts. base_url=$BaseUrl error=$lastErrorMessage"
    }
}

Write-Host "selected_model=$($response.model)"
$replyText = [string]$response.choices[0].message.content
if ($replyText.Length -gt 240) {
    $replyPreview = $replyText.Substring(0, 240) + "..."
}
else {
    $replyPreview = $replyText
}
Write-Host "reply_preview=$replyPreview"
Write-Host "reply_length=$($replyText.Length)"
Write-Host "status=OK"
exit 0
