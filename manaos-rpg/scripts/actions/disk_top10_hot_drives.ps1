param(
  [int]$Top = 10,
  [int]$AlertPercent = 80,
  [int]$MaxDrives = 2
)

$ErrorActionPreference = 'Stop'
$Top = [Math]::Max(1, [Math]::Min($Top, 100))
$AlertPercent = [Math]::Max(1, [Math]::Min($AlertPercent, 99))
$MaxDrives = [Math]::Max(1, [Math]::Min($MaxDrives, 8))

$drives = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" |
  ForEach-Object {
    $size = [double]($_.Size)
    $free = [double]($_.FreeSpace)
    if ($size -le 0) { return }
    $usedPct = [math]::Round((($size - $free) / $size) * 100, 1)
    [PSCustomObject]@{
      Drive = [string]$_.DeviceID + '\\'
      UsedPercent = $usedPct
      SizeGB = [math]::Round($size / 1GB, 2)
      FreeGB = [math]::Round($free / 1GB, 2)
    }
  } |
  Where-Object { $_.UsedPercent -ge $AlertPercent } |
  Sort-Object UsedPercent -Descending |
  Select-Object -First $MaxDrives

if (-not $drives -or @($drives).Count -eq 0) {
  Write-Host "[INFO] no drives above threshold (${AlertPercent}%)" -ForegroundColor Yellow
  exit 0
}

Write-Host "[INFO] hot drives:" -ForegroundColor Cyan
$drives | Format-Table -AutoSize

foreach ($d in $drives) {
  $root = [string]$d.Drive
  Write-Host "`n[INFO] scanning $root top=$Top" -ForegroundColor Cyan

  $items = Get-ChildItem -Path $root -File -Recurse -Force -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending |
    Select-Object -First $Top FullName, Length, LastWriteTime

  if (-not $items -or @($items).Count -eq 0) {
    Write-Host "[INFO] no files found in $root" -ForegroundColor Yellow
    continue
  }

  $items |
    Select-Object @{Name='SizeGB';Expression={[Math]::Round($_.Length / 1GB, 3)}}, FullName, LastWriteTime |
    Format-Table -AutoSize

  $summary = [PSCustomObject]@{
    drive = $root
    used_percent = $d.UsedPercent
    top = $Top
    count = @($items).Count
    largest_bytes = [int64]$items[0].Length
    largest_path = [string]$items[0].FullName
  }

  Write-Output "`n[JSON_SUMMARY]"
  $summary | ConvertTo-Json -Depth 3
}
