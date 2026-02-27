param(
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$v2Script = Join-Path $scriptDir "run_image_pipeline_probe_once_v2.ps1"

if (-not (Test-Path $v2Script)) {
    throw "v2 probe script not found: $v2Script"
}

$invokeArgs = @{}
if (-not [string]::IsNullOrWhiteSpace($ConfigFile)) {
    $invokeArgs.ConfigFile = $ConfigFile
}

& $v2Script @invokeArgs
exit $LASTEXITCODE
