param(
  [int]$TopFolders = 8,
  [Alias('TopFiles')]
  [int]$TopFileCount = 12,
  [int]$RecentDays = 14,
  [int]$MinFileGB = 1
)

$ErrorActionPreference = 'Stop'
$TopFolders = [Math]::Max(3, [Math]::Min($TopFolders, 30))
$TopFileCount = [Math]::Max(3, [Math]::Min($TopFileCount, 100))
$RecentDays = [Math]::Max(1, [Math]::Min($RecentDays, 365))
$MinFileGB = [Math]::Max(1, [Math]::Min($MinFileGB, 100))

function Get-FolderSizeGB([string]$path) {
  try {
    $sum = (
      Get-ChildItem -Path $path -File -Recurse -Force -ErrorAction SilentlyContinue |
      Select-Object -First 20000 |
      Measure-Object -Property Length -Sum
    ).Sum
    if (-not $sum) { return 0.0 }
    return [Math]::Round(([double]$sum / 1GB), 3)
  } catch {
    return 0.0
  }
}

$focusFolders = @(
  # C: OS/運用系（掃除候補）
  'C:\Windows\Temp',
  'C:\Users\mana4\AppData\Local\Temp',
  'C:\Users\mana4\Downloads',
  'C:\Users\mana4\Desktop',
  # D: AI系（容量観測・整理候補）
  'D:\ComfyUI\output',
  'D:\gallery_images',
  'D:\AI_Data',
  'D:\AI_Storage',
  'D:\AI_Storage\Models',
  'D:\Downloads'
)

$existing = @($focusFolders | Where-Object { Test-Path $_ })
$folderRows = @(
  $existing | ForEach-Object {
    [PSCustomObject]@{
      path = $_
      size_gb = Get-FolderSizeGB $_
    }
  }
) | Sort-Object size_gb -Descending | Select-Object -First $TopFolders

$since = (Get-Date).AddDays(-$RecentDays)
$minBytes = [int64]$MinFileGB * 1GB

$allTargets = @($existing)
$fileRows = @()
foreach ($root in $allTargets) {
  try {
    $fileRows += Get-ChildItem -Path $root -File -Recurse -Force -ErrorAction SilentlyContinue |
      Where-Object { $_.LastWriteTime -ge $since -and $_.Length -ge $minBytes }
  } catch {
    continue
  }
}

$topFiles = @($fileRows | Sort-Object Length -Descending | Select-Object -First $TopFileCount)

Write-Host "[INFO] C(OS) / D(AI) 整理候補フォルダ（サイズ順）" -ForegroundColor Cyan
$folderRows | Format-Table -AutoSize

Write-Host "`n[INFO] 最近 ${RecentDays}日・${MinFileGB}GB以上の大きいファイル" -ForegroundColor Cyan
$topFiles |
  Select-Object @{Name='SizeGB';Expression={[Math]::Round($_.Length/1GB,3)}}, FullName, LastWriteTime |
  Format-Table -AutoSize

Write-Output "`n[JSON_SUMMARY]"
[PSCustomObject]@{
  focus_folder_count = @($folderRows).Count
  large_file_count = @($topFiles).Count
  top_folders = @($folderRows)
  top_files = @(
    $topFiles | ForEach-Object {
      [PSCustomObject]@{
        path = [string]$_.FullName
        size_gb = [Math]::Round($_.Length/1GB,3)
        last_write = $_.LastWriteTime.ToString('s')
      }
    }
  )
} | ConvertTo-Json -Depth 6
