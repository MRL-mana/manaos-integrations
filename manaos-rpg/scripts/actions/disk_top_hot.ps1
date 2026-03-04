param(
  [int]$Top = 10,
  [double]$MinUsedPercent = 80
)

$ErrorActionPreference = 'Stop'
$Top = [Math]::Max(1, [Math]::Min($Top, 100))
$minPct = [Math]::Max(0, [Math]::Min($MinUsedPercent, 100))

$drives = Get-PSDrive -PSProvider FileSystem | ForEach-Object {
  $used = 0.0
  $pct = 0.0
  if ($_.Used -gt 0 -or $_.Free -gt 0) {
    $used = [double]$_.Used
    $total = [double]$_.Used + [double]$_.Free
    if ($total -gt 0) {
      $pct = ($used / $total) * 100.0
    }
  }
  [PSCustomObject]@{
    Root = $_.Root
    UsedPercent = [Math]::Round($pct, 1)
  }
} | Where-Object { $_.UsedPercent -ge $minPct } | Sort-Object UsedPercent -Descending

if (-not $drives -or @($drives).Count -eq 0) {
  Write-Host "[INFO] no drives over threshold (${minPct}%)" -ForegroundColor Yellow
  exit 0
}

$allSummary = @()
foreach ($d in $drives) {
  $root = [string]$d.Root
  Write-Host "`n[INFO] scanning $root used=$($d.UsedPercent)% (top=$Top)" -ForegroundColor Cyan

  $items = Get-ChildItem -Path $root -File -Recurse -Force -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending |
    Select-Object -First $Top FullName, Length, LastWriteTime

  if (-not $items -or @($items).Count -eq 0) {
    Write-Host "[INFO] no files found on $root" -ForegroundColor Yellow
    $allSummary += [PSCustomObject]@{ drive = $root; used_percent = $d.UsedPercent; count = 0; largest_bytes = 0; largest_path = '' }
    continue
  }

  $items |
    Select-Object @{Name='SizeGB';Expression={[Math]::Round($_.Length / 1GB, 3)}}, FullName, LastWriteTime |
    Format-Table -AutoSize

  $allSummary += [PSCustomObject]@{
    drive = $root
    used_percent = $d.UsedPercent
    count = @($items).Count
    largest_bytes = [int64]$items[0].Length
    largest_path = [string]$items[0].FullName
  }
}

Write-Output "`n[JSON_SUMMARY]"
$allSummary | ConvertTo-Json -Depth 4
