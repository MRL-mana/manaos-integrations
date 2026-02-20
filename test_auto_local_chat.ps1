param(
    [string]$BaseUrl = "http://127.0.0.1:5211/v1",
    [string]$Model = "auto-local",
    [int]$MaxRetries = 5,
    [int]$RetryDelaySeconds = 2
)

$ErrorActionPreference = "Stop"

$body = @{
    model = $Model
    messages = @(
        @{ role = "system"; content = "You are a concise coding assistant." },
        @{ role = "user"; content = "Write a short Python function that returns the sum of a list of numbers." }
    )
    temperature = 0.2
} | ConvertTo-Json -Depth 8

$response = $null
$lastErrorMessage = $null

for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 20
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
    throw "auto-local chat test failed after $MaxRetries attempts. base_url=$BaseUrl error=$lastErrorMessage"
}

Write-Host "selected_model=$($response.model)"
Write-Host "reply=$($response.choices[0].message.content)"
Write-Host "status=OK"
