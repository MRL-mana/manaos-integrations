$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$pidFile = Join-Path $root '.pixel7_edge_watch.pid'
$statusFile = Join-Path $root '.pixel7_edge_watch.status.json'

$running = $false
$pidValue = $null
if (Test-Path $pidFile) {
    $pidText = (Get-Content -Raw -ErrorAction SilentlyContinue $pidFile).Trim()
    if ($pidText -match '^\d+$') {
        $pidValue = [int]$pidText
        $p = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        $running = [bool]$p
    }
}

$obj = [ordered]@{
    running = $running
    pid = $pidValue
    status_file_exists = (Test-Path $statusFile)
    status = $null
}

if (Test-Path $statusFile) {
    try {
        $obj.status = Get-Content -Raw -Encoding UTF8 $statusFile | ConvertFrom-Json
    } catch {
        $obj.status = @{ parse_error = $_.Exception.Message }
    }
}

$obj | ConvertTo-Json -Depth 8
