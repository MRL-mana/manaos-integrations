param(
    [string]$BaseUrl = "http://127.0.0.1:5211/v1",
    [string]$Model = "auto-local"
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

$response = Invoke-RestMethod -Uri "$BaseUrl/chat/completions" -Method Post -ContentType "application/json" -Body $body

Write-Host "selected_model=$($response.model)"
Write-Host "reply=$($response.choices[0].message.content)"
Write-Host "status=OK"
