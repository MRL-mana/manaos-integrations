param(
  [int]$Top = 10
)

$ErrorActionPreference = 'Stop'
$Top = [Math]::Max(1, [Math]::Min($Top, 100))
$driveRoot = 'H:\'

if (-not (Test-Path $driveRoot)) {
  Write-Error "Drive not found: $driveRoot"
  exit 1
}

Write-Host "[INFO] scanning largest files on $driveRoot (top=$Top)" -ForegroundColor Cyan

$items = Get-ChildItem -Path $driveRoot -File -Recurse -Force -ErrorAction SilentlyContinue |
  Sort-Object Length -Descending |
  Select-Object -First $Top FullName, Length, LastWriteTime

if (-not $items -or $items.Count -eq 0) {
  Write-Host "[INFO] no files found on $driveRoot" -ForegroundColor Yellow
  exit 0
}

$items |
  Select-Object @{Name='SizeGB';Expression={[Math]::Round($_.Length / 1GB, 3)}}, FullName, LastWriteTime |
  Format-Table -AutoSize

$summary = [PSCustomObject]@{
  drive = $driveRoot
  top = $Top
  count = @($items).Count
  largest_bytes = [int64]$items[0].Length
  largest_path = [string]$items[0].FullName
}

Write-Output "`n[JSON_SUMMARY]"
$summary | ConvertTo-Json -Depth 3
