param(
    [string]$Owner = "MRL-mana",
    [string]$Repo = "manaos-integrations",
    [string]$WebuiSecretKey = "",
    [System.Security.SecureString]$CodeServerPasswordSecure,
    [System.Security.SecureString]$PostgresPasswordSecure,
    [System.Security.SecureString]$OpsExecBearerTokenSecure,
    [string]$WebhookUrl = "",
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [switch]$GenerateMissing,
    [switch]$SkipWebhookSecrets
)

$ErrorActionPreference = "Stop"

function New-RandomToken {
    param([int]$Bytes = 24)
    $raw = New-Object byte[] $Bytes
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($raw)
    return [Convert]::ToBase64String($raw).Replace("+", "a").Replace("/", "b").TrimEnd('=')
}

function Resolve-Value {
    param(
        [string]$Current,
        [string]$Fallback,
        [switch]$AllowGenerate
    )

    if (-not [string]::IsNullOrWhiteSpace($Current)) {
        return $Current
    }

    if (-not [string]::IsNullOrWhiteSpace($Fallback)) {
        return $Fallback
    }

    if ($AllowGenerate) {
        return (New-RandomToken)
    }

    return ""
}

function ConvertTo-PlainText {
    param([System.Security.SecureString]$Value)

    if ($null -eq $Value) {
        return ""
    }

    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Set-GitHubSecret {
    param(
        [string]$Name,
        [string]$Value,
        [string]$Repository
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        Write-Host "[SKIP] $Name (empty)" -ForegroundColor Yellow
        return
    }

    gh secret set $Name --repo $Repository --body $Value | Out-Null
    Write-Host "[OK] $Name" -ForegroundColor Green
}

$repoSlug = "$Owner/$Repo"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is not installed. Install gh and run: gh auth login"
}

gh auth status | Out-Null

$codeServerPasswordText = ConvertTo-PlainText -Value $CodeServerPasswordSecure
$postgresPasswordText = ConvertTo-PlainText -Value $PostgresPasswordSecure
$opsExecBearerTokenText = ConvertTo-PlainText -Value $OpsExecBearerTokenSecure

$WebuiSecretKey = Resolve-Value -Current $WebuiSecretKey -Fallback $env:BLUEPRINT_WEBUI_SECRET_KEY -AllowGenerate:$GenerateMissing
$CodeServerPassword = Resolve-Value -Current $codeServerPasswordText -Fallback $env:BLUEPRINT_CODE_SERVER_PASSWORD -AllowGenerate:$GenerateMissing
$PostgresPassword = Resolve-Value -Current $postgresPasswordText -Fallback $env:BLUEPRINT_POSTGRES_PASSWORD -AllowGenerate:$GenerateMissing
$OpsExecBearerToken = Resolve-Value -Current $opsExecBearerTokenText -Fallback $env:BLUEPRINT_OPS_EXEC_BEARER_TOKEN -AllowGenerate:$GenerateMissing

if ([string]::IsNullOrWhiteSpace($WebuiSecretKey) -or
    [string]::IsNullOrWhiteSpace($CodeServerPassword) -or
    [string]::IsNullOrWhiteSpace($PostgresPassword) -or
    [string]::IsNullOrWhiteSpace($OpsExecBearerToken)) {
    throw "Missing core secrets. Provide values or use -GenerateMissing."
}

Write-Host "Setting core blueprint CI secrets to $repoSlug" -ForegroundColor Cyan
Set-GitHubSecret -Name "BLUEPRINT_WEBUI_SECRET_KEY" -Value $WebuiSecretKey -Repository $repoSlug
Set-GitHubSecret -Name "BLUEPRINT_CODE_SERVER_PASSWORD" -Value $CodeServerPassword -Repository $repoSlug
Set-GitHubSecret -Name "BLUEPRINT_POSTGRES_PASSWORD" -Value $PostgresPassword -Repository $repoSlug
Set-GitHubSecret -Name "BLUEPRINT_OPS_EXEC_BEARER_TOKEN" -Value $OpsExecBearerToken -Repository $repoSlug

if (-not $SkipWebhookSecrets) {
    if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
        $WebhookUrl = $env:MANAOS_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
        $WebhookMention = $env:MANAOS_WEBHOOK_MENTION
    }

    $notifyOnSuccessValue = if ($NotifyOnSuccess) { "true" } else { "false" }

    Write-Host "Setting optional webhook secrets to $repoSlug" -ForegroundColor Cyan
    Set-GitHubSecret -Name "MANAOS_BLUEPRINT_WEBHOOK_URL" -Value $WebhookUrl -Repository $repoSlug
    Set-GitHubSecret -Name "MANAOS_BLUEPRINT_WEBHOOK_FORMAT" -Value $WebhookFormat -Repository $repoSlug
    Set-GitHubSecret -Name "MANAOS_BLUEPRINT_WEBHOOK_MENTION" -Value $WebhookMention -Repository $repoSlug
    Set-GitHubSecret -Name "MANAOS_BLUEPRINT_NOTIFY_ON_SUCCESS" -Value $notifyOnSuccessValue -Repository $repoSlug
}

Write-Host "[OK] Blueprint CI secrets setup completed" -ForegroundColor Green
