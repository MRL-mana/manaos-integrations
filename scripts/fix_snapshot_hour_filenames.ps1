param(
  [string]$Date = ""
)

$ErrorActionPreference = "Stop"

$baseDir = "C:\Users\mana4\Desktop\manaos_integrations\snapshots"

if ([string]::IsNullOrWhiteSpace($Date)) {
  $Date = (Get-Date -Format "yyyy-MM-dd")
}

$dir = Join-Path $baseDir $Date
if (-not (Test-Path $dir)) {
  Write-Host ("[WARN] Date dir not found: {0}" -f $dir)
  exit 0
}

Write-Host ("[INFO] Fixing filenames in: {0}" -f $dir)

$files = Get-ChildItem $dir -File | Where-Object { $_.Name -match '^\s+\d+\.json$' }
foreach ($f in $files) {
  $trim = $f.Name.Trim()
  if ($trim -match '^(\d+)\.json$') {
    $n = [int]$matches[1]
    $newName = ("{0:d2}.json" -f $n)
    $dest = Join-Path $dir $newName
    if (Test-Path $dest) {
      Write-Host ("[WARN] Skip (dest exists): {0} -> {1}" -f $f.Name, $newName)
      continue
    }
    Move-Item -LiteralPath $f.FullName -Destination $dest
    Write-Host ("[OK] Renamed: {0} -> {1}" -f $f.Name, $newName)
  }
}

Write-Host "[OK] Done."

