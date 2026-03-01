param(
    [Parameter(Mandatory = $true)]
    [string]$WebhookUrl,
    [Parameter(Mandatory = $true)]
    [string]$Text,
    [ValidateSet('generic', 'slack', 'discord')]
    [string]$Format = 'slack',
    [string]$Mention = ''
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
    throw "webhook url is empty"
}

$content = if ([string]::IsNullOrWhiteSpace($Mention)) { $Text } else { "$Mention`n$Text" }
$payloadObj = switch ($Format) {
    'discord' { @{ content = $content } }
    'generic' { @{ text = $content } }
    default { @{ text = $content } }
}
$payload = $payloadObj | ConvertTo-Json -Depth 4

try {
    Invoke-RestMethod -Uri $WebhookUrl -Method Post -ContentType "application/json" -Body $payload | Out-Null
    exit 0
}
catch {
    Write-Error "slack webhook post failed: $($_.Exception.Message)"
    exit 1
}
