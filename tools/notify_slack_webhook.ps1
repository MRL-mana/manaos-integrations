param(
    [Parameter(Mandatory = $true)]
    [string]$WebhookUrl,
    [Parameter(Mandatory = $true)]
    [string]$Text,
    [ValidateSet('generic', 'slack', 'discord')]
    [string]$Format = 'slack',
    [string]$Mention = '',
    [ValidateRange(1, 10)]
    [int]$RetryCount = 3,
    [ValidateRange(0, 60)]
    [int]$InitialDelaySec = 1,
    [ValidateRange(1.0, 5.0)]
    [double]$BackoffFactor = 2.0
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

$delaySec = [double]$InitialDelaySec
for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
    try {
        Invoke-RestMethod -Uri $WebhookUrl -Method Post -ContentType "application/json" -Body $payload | Out-Null
        exit 0
    }
    catch {
        if ($attempt -ge $RetryCount) {
            Write-Error "slack webhook post failed after $attempt attempts: $($_.Exception.Message)"
            exit 1
        }

        Write-Warning ("slack webhook post failed (attempt {0}/{1}): {2}" -f $attempt, $RetryCount, $_.Exception.Message)
        if ($delaySec -gt 0) {
            Start-Sleep -Seconds ([Math]::Ceiling($delaySec))
        }
        $delaySec = $delaySec * $BackoffFactor
    }
}
