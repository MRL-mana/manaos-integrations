param(
    [Parameter(Mandatory = $true)]
    [string]$WebhookUrl,
    [Parameter(Mandatory = $true)]
    [string]$Text
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
    throw "webhook url is empty"
}

$payload = @{ text = $Text } | ConvertTo-Json -Depth 4

try {
    Invoke-RestMethod -Uri $WebhookUrl -Method Post -ContentType "application/json" -Body $payload | Out-Null
    exit 0
}
catch {
    Write-Error "slack webhook post failed: $($_.Exception.Message)"
    exit 1
}
