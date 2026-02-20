param(
    [string]$WorkspaceRoot = "C:\Users\mana4\Desktop",
    [int]$LogOlderThanDays = 14,
    [int]$TmpOlderThanDays = 30
)

$ErrorActionPreference = "Stop"
$repoRoot = Join-Path $WorkspaceRoot "manaos_integrations"
$reportDir = Join-Path $repoRoot "Reports"
$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$outFile = Join-Path $reportDir "Maintenance_DryRun_$stamp.md"

New-Item -ItemType Directory -Path $reportDir -Force | Out-Null

function Get-FolderSizeGB {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return 0 }
    $sum = (Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    if (-not $sum) { $sum = 0 }
    return [math]::Round($sum / 1GB, 2)
}

$desktopTop = Get-ChildItem -Path $WorkspaceRoot -Directory -ErrorAction SilentlyContinue |
    ForEach-Object {
        [PSCustomObject]@{
            Name = $_.Name
            SizeGB = Get-FolderSizeGB -Path $_.FullName
        }
    } |
    Sort-Object SizeGB -Descending |
    Select-Object -First 15

$logPath = Join-Path $repoRoot "logs"
$logCandidates = @()
if (Test-Path $logPath) {
    $logCandidates = Get-ChildItem -Path $logPath -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$LogOlderThanDays) } |
        Select-Object FullName, Length, LastWriteTime
}

$tmpPath = Join-Path $WorkspaceRoot ".tmp.driveupload"
$tmpCandidates = @()
if (Test-Path $tmpPath) {
    $tmpCandidates = Get-ChildItem -Path $tmpPath -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$TmpOlderThanDays) } |
        Select-Object -First 1000 FullName, Length, LastWriteTime
}

$gitStatus = @()
try {
    $gitStatus = git -C $repoRoot status --short 2>$null
} catch {
    $gitStatus = @("(git status 取得失敗)")
}

$logMB = [math]::Round((($logCandidates | Measure-Object Length -Sum).Sum / 1MB), 2)
$tmpMB = [math]::Round((($tmpCandidates | Measure-Object Length -Sum).Sum / 1MB), 2)
if (-not $logMB) { $logMB = 0 }
if (-not $tmpMB) { $tmpMB = 0 }

$lines = @()
$lines += "# Maintenance Dry Run"
$lines += ""
$lines += "- Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$lines += "- Mode: DRY RUN ONLY (no deletion)"
$lines += ""
$lines += "## Capacity Top 15 (Desktop)"
$lines += ""
$lines += "| Name | SizeGB |"
$lines += "|---|---:|"
foreach ($row in $desktopTop) {
    $lines += "| $($row.Name) | $($row.SizeGB) |"
}
$lines += ""
$lines += "## Cleanup Candidates (No Action)"
$lines += ""
$lines += "- logs older than $LogOlderThanDays days: $($logCandidates.Count) files / $logMB MB"
$lines += "- .tmp.driveupload older than $TmpOlderThanDays days: $($tmpCandidates.Count) files / $tmpMB MB"
$lines += ""
$lines += "## Git Status (Short)"
$lines += ""
$lines += "```"
$lines += ($gitStatus -join [Environment]::NewLine)
$lines += "```"
$lines += ""
$lines += "## Notes"
$lines += ""
$lines += "- This script does not delete or move any file."
$lines += "- Review this report before any cleanup execution."

$lines -join [Environment]::NewLine | Out-File -FilePath $outFile -Encoding UTF8
Write-Output $outFile
