param(
    [int]$Bytes = 32,
    [switch]$NoWriteFile
)

$ErrorActionPreference = 'Stop'

if ($Bytes -lt 16) { $Bytes = 16 }
if ($Bytes -gt 64) { $Bytes = 64 }

$buf = New-Object byte[] $Bytes
[System.Security.Cryptography.RandomNumberGenerator]::Fill($buf)
$token = [Convert]::ToBase64String($buf).TrimEnd('=')

$tokenFile = Join-Path $PSScriptRoot '.pixel7_api_token.txt'
if (-not $NoWriteFile) {
    try {
        Set-Content -Encoding UTF8 -NoNewline -Path $tokenFile -Value $token
    } catch {
        Write-Host ("[WARN] failed to write token file: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
}

Write-Host '=== Pixel7 API Token ===' -ForegroundColor Cyan
Write-Host $token -ForegroundColor Green
Write-Host ''
Write-Host '[Windows (PowerShell)]' -ForegroundColor Gray
Write-Host ("$env:PIXEL7_API_TOKEN='{0}'" -f $token) -ForegroundColor White
Write-Host ''
Write-Host '[Termux (bash)]' -ForegroundColor Gray
Write-Host ("export PIXEL7_API_TOKEN='{0}'" -f $token) -ForegroundColor White
Write-Host ''
if (-not $NoWriteFile) {
    Write-Host ("saved: {0}" -f $tokenFile) -ForegroundColor DarkGray
}
Write-Host ''
Write-Host 'OK' -ForegroundColor Green
