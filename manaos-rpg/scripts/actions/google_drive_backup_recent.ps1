param(
  [int]$MaxFiles = 20,
  [int]$RecentHours = 24,
  [int]$MinSizeMB = 5,
  [string]$FolderPath = "ManaOS_Backup/D_AI"
)

$ErrorActionPreference = 'Stop'
$MaxFiles = [Math]::Max(1, [Math]::Min($MaxFiles, 200))
$RecentHours = [Math]::Max(1, [Math]::Min($RecentHours, 24 * 30))
$MinSizeMB = [Math]::Max(0.001, [Math]::Min($MinSizeMB, 1024 * 10))

$candidateRoots = @(
  'D:\AI_Storage\organized_from_c',
  'D:\AI_Storage\Models',
  'D:\ComfyUI\output',
  'D:\gallery_images',
  'D:\AI_Data',
  'D:\Downloads'
)

$roots = @($candidateRoots | Where-Object { Test-Path $_ })
if (-not $roots -or $roots.Count -eq 0) {
  Write-Host "[INFO] no backup roots found" -ForegroundColor Yellow
  exit 0
}

$since = (Get-Date).AddHours(-$RecentHours)
$minBytes = [int64]$MinSizeMB * 1MB

Write-Host "[INFO] backup roots: $($roots -join ', ')" -ForegroundColor Cyan
Write-Host "[INFO] filter: modified since $($since.ToString('s')), min size ${MinSizeMB}MB" -ForegroundColor Cyan

$files = @()
foreach ($root in $roots) {
  try {
    $files += Get-ChildItem -Path $root -File -Recurse -Force -ErrorAction SilentlyContinue |
      Where-Object { $_.LastWriteTime -ge $since -and $_.Length -ge $minBytes }
  } catch {
    continue
  }
}

$targets = @($files | Sort-Object LastWriteTime -Descending | Select-Object -First $MaxFiles)
if (-not $targets -or $targets.Count -eq 0) {
  Write-Host "[INFO] no candidate files for backup" -ForegroundColor Yellow
  exit 0
}

$manifestRows = @(
  $targets | ForEach-Object {
    [PSCustomObject]@{
      path = [string]$_.FullName
      name = [string]$_.Name
      size_bytes = [int64]$_.Length
      last_write = $_.LastWriteTime.ToString('s')
    }
  }
)

$manifestPath = [System.IO.Path]::GetTempFileName()
$manifestJson = [System.IO.Path]::ChangeExtension($manifestPath, '.json')
Move-Item -Path $manifestPath -Destination $manifestJson -Force
$manifestRows | ConvertTo-Json -Depth 4 | Set-Content -Path $manifestJson -Encoding UTF8

$scriptPy = Join-Path $PSScriptRoot 'google_drive_backup_recent.py'
if (-not (Test-Path $scriptPy)) {
  Write-Error "helper script not found: $scriptPy"
  exit 2
}

Write-Host "[INFO] uploading $($targets.Count) files to Google Drive path '$FolderPath' ..." -ForegroundColor Cyan
$out = & py -3.10 $scriptPy --manifest $manifestJson --folder-path $FolderPath
$code = $LASTEXITCODE

Remove-Item -Path $manifestJson -Force -ErrorAction SilentlyContinue

if ($out) {
  $out | ForEach-Object { Write-Output $_ }
}

if ($code -ne 0) {
  Write-Error "google drive backup failed (exit=$code)"
  exit $code
}

Write-Output "`n[JSON_SUMMARY]"
[PSCustomObject]@{
  ok = $true
  requested = @($targets).Count
  roots = $roots
  folder_path = $FolderPath
  recent_hours = $RecentHours
  min_size_mb = $MinSizeMB
} | ConvertTo-Json -Depth 4
