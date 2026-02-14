param(
    [string]$ConfigPath = "manaos_integrations/remi_android_shortcuts.json"
)

$ErrorActionPreference = "Stop"

function Is-DangerousName([string]$name) {
    $n = $name.ToLowerInvariant()
    return (
        $n -match 'emergency' -or
        $n -match 'stop' -or
        $n -match 'cleanup'
    )
}

if (-not (Test-Path $ConfigPath)) {
    throw "Config not found: $ConfigPath"
}

$json = Get-Content -Raw -Encoding UTF8 $ConfigPath | ConvertFrom-Json

$rows = @()
foreach ($cat in $json.categories) {
    foreach ($sc in $cat.shortcuts) {
        $rows += [pscustomobject]@{
            Category = $cat.name
            Name = [string]$sc.name
            Method = [string]$sc.method
            Url = [string]$sc.url
            ResponseHandling = [string]$sc.responseHandling
            Dangerous = (Is-DangerousName([string]$sc.name))
        }
    }
}

$rows | Sort-Object Category, Name | Format-Table -AutoSize
