param(
  [int]$MaxFiles = 100,
  [int]$RecentDays = 30,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$MaxFiles = [Math]::Max(1, [Math]::Min($MaxFiles, 2000))
$RecentDays = [Math]::Max(1, [Math]::Min($RecentDays, 365))

$sources = @(
  'C:\ComfyUI\output',
  'C:\Users\mana4\Desktop\gallery_images',
  'C:\Users\mana4\Desktop\AI_Data'
)

$destBase = @('D:\AI_Data', 'D:\AI_Storage', 'D:\') | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $destBase) {
  Write-Error 'Dドライブが見つかりません（D=AI運用前提）'
  exit 2
}
$destRoot = Join-Path $destBase 'organized_from_c'

$validExt = @(
  '.png','.jpg','.jpeg','.webp','.bmp','.avif','.heic','.heif',
  '.mp4','.mov','.mkv','.webm','.gif',
  '.safetensors','.ckpt','.pt','.pth',
  '.json','.txt','.csv'
)

$since = (Get-Date).AddDays(-$RecentDays)
$exists = @($sources | Where-Object { Test-Path $_ })
if (-not $exists -or $exists.Count -eq 0) {
  Write-Host '[INFO] organize source not found on C drive' -ForegroundColor Yellow
  exit 0
}

$targets = @()
foreach ($src in $exists) {
  try {
    $targets += Get-ChildItem -Path $src -File -Recurse -Force -ErrorAction SilentlyContinue |
      Where-Object {
        $_.LastWriteTime -ge $since -and
        ($validExt -contains $_.Extension.ToLowerInvariant())
      }
  } catch {
    continue
  }
}

$targets = @($targets | Sort-Object LastWriteTime -Descending | Select-Object -First $MaxFiles)
if (-not $targets -or $targets.Count -eq 0) {
  Write-Host '[INFO] move target not found' -ForegroundColor Yellow
  exit 0
}

$moved = @()
$skipped = @()

foreach ($file in $targets) {
  $day = $file.LastWriteTime.ToString('yyyyMMdd')
  $destDir = Join-Path $destRoot $day
  $destPath = Join-Path $destDir $file.Name

  if (Test-Path $destPath) {
    $nameNoExt = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $ext = [System.IO.Path]::GetExtension($file.Name)
    $destPath = Join-Path $destDir ("{0}_{1}{2}" -f $nameNoExt, (Get-Date -Format 'HHmmssfff'), $ext)
  }

  if ($DryRun) {
    $moved += [PSCustomObject]@{ from = $file.FullName; to = $destPath; size_mb = [Math]::Round($file.Length / 1MB, 2) }
    continue
  }

  try {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    Move-Item -Path $file.FullName -Destination $destPath -Force
    $moved += [PSCustomObject]@{ from = $file.FullName; to = $destPath; size_mb = [Math]::Round($file.Length / 1MB, 2) }
  } catch {
    $skipped += [PSCustomObject]@{ path = $file.FullName; reason = $_.Exception.Message }
  }
}

Write-Host "[INFO] organize result moved=$(@($moved).Count) skipped=$(@($skipped).Count) dryrun=$($DryRun.IsPresent)" -ForegroundColor Cyan
Write-Output "`n[JSON_SUMMARY]"
[PSCustomObject]@{
  ok = $true
  dry_run = [bool]$DryRun.IsPresent
  moved_count = @($moved).Count
  skipped_count = @($skipped).Count
  dest_root = $destRoot
  moved = @($moved | Select-Object -First 30)
  skipped = @($skipped | Select-Object -First 30)
} | ConvertTo-Json -Depth 6
