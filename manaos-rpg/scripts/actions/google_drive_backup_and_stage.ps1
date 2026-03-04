param(
  [int]$MaxFiles = 30,
  [int]$RecentHours = 72,
  [int]$MinSizeMB = 5,
  [string]$FolderPath = 'ManaOS_Backup/D_AI',
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$base = Join-Path $PSScriptRoot 'google_drive_backup_recent.ps1'
if (-not (Test-Path $base)) {
  Write-Error "base script not found: $base"
  exit 2
}

$temp = [System.IO.Path]::GetTempFileName()
try {
  $args = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $base,
    '-MaxFiles', "$MaxFiles",
    '-RecentHours', "$RecentHours",
    '-MinSizeMB', "$MinSizeMB",
    '-FolderPath', $FolderPath
  )

  $rawOut = & pwsh @args
  $exitCode = $LASTEXITCODE
  if ($rawOut) {
    $rawOut | Set-Content -Path $temp -Encoding UTF8
    $rawOut | ForEach-Object { Write-Output $_ }
  }
  if ($exitCode -ne 0) {
    Write-Error "backup step failed (exit=$exitCode)"
    exit $exitCode
  }

  $jsonLine = $null
  if (Test-Path $temp) {
    $lines = Get-Content -Path $temp -Encoding UTF8
    foreach ($line in $lines) {
      $trim = [string]$line
      if ($trim -notmatch '^\s*\{.*\}\s*$') { continue }
      try {
        $objTry = $trim | ConvertFrom-Json -ErrorAction Stop
        if ($null -ne $objTry) {
          if ($objTry.PSObject.Properties.Name -contains 'uploaded_items' -or $objTry.PSObject.Properties.Name -contains 'reason') {
            $jsonLine = $trim
          }
        }
      } catch {
        continue
      }
    }
  }

  if (-not $jsonLine) {
    Write-Output "`n[JSON_SUMMARY]"
    [PSCustomObject]@{ ok = $true; staged_count = 0; reason = 'no_json_from_backup' } | ConvertTo-Json -Depth 4
    exit 0
  }

  $obj = $jsonLine | ConvertFrom-Json
  $uploaded = @($obj.uploaded_items)
  if (-not $uploaded -or $uploaded.Count -eq 0) {
    Write-Output "`n[JSON_SUMMARY]"
    [PSCustomObject]@{ ok = $true; staged_count = 0; reason = 'nothing_uploaded' } | ConvertTo-Json -Depth 4
    exit 0
  }

  $stageBase = @('D:\AI_Data', 'D:\AI_Storage', 'D:\') | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $stageBase) {
    Write-Output "`n[JSON_SUMMARY]"
    [PSCustomObject]@{ ok = $false; reason = 'd_drive_missing_for_stage' } | ConvertTo-Json -Depth 4
    exit 2
  }
  $stageRoot = Join-Path $stageBase 'backup_staged'
  $stageDir = Join-Path $stageRoot (Get-Date -Format 'yyyyMMdd')
  New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

  $staged = @()
  $failed = @()
  foreach ($row in $uploaded) {
    $src = [string]$row.path
    if (-not (Test-Path $src)) {
      $failed += [PSCustomObject]@{ path = $src; reason = 'missing_after_upload' }
      continue
    }
    $name = [System.IO.Path]::GetFileName($src)
    $dst = Join-Path $stageDir $name
    if (Test-Path $dst) {
      $nameNoExt = [System.IO.Path]::GetFileNameWithoutExtension($name)
      $ext = [System.IO.Path]::GetExtension($name)
      $dst = Join-Path $stageDir ("{0}_{1}{2}" -f $nameNoExt, (Get-Date -Format 'HHmmssfff'), $ext)
    }
    try {
      if ($DryRun) {
        $staged += [PSCustomObject]@{ from = $src; to = $dst; file_id = [string]$row.file_id }
      } else {
        Move-Item -Path $src -Destination $dst -Force
        $staged += [PSCustomObject]@{ from = $src; to = $dst; file_id = [string]$row.file_id }
      }
    } catch {
      $failed += [PSCustomObject]@{ path = $src; reason = $_.Exception.Message }
    }
  }

  Write-Output "`n[JSON_SUMMARY]"
  [PSCustomObject]@{
    ok = $true
    dry_run = [bool]$DryRun.IsPresent
    uploaded_count = @($uploaded).Count
    staged_count = @($staged).Count
    failed_count = @($failed).Count
    stage_dir = $stageDir
    staged = @($staged | Select-Object -First 30)
    failed = @($failed | Select-Object -First 30)
  } | ConvertTo-Json -Depth 6
}
finally {
  Remove-Item -Path $temp -Force -ErrorAction SilentlyContinue
}
