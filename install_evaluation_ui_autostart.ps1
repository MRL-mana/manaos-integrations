# 画像評価UI(9601) を Windows ログオン時に自動起動するショートカットを登録/解除する
# 実行: PowerShell で .\install_evaluation_ui_autostart.ps1 または .\install_evaluation_ui_autostart.ps1 -Uninstall

param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutName = "EvaluationUI9601.lnk"
$shortcutPath = Join-Path $startupFolder $shortcutName

# pythonw を探す（コンソール非表示で起動用）
$pythonw = Get-Command pythonw -ErrorAction SilentlyContinue
if (-not $pythonw) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { Write-Error "python / pythonw not found" }
    $pythonw = $py
}
$exe = $pythonw.Source
$launcher = Join-Path $scriptDir "auto_start_evaluation_ui_9601.py"

if ($Uninstall) {
    if (Test-Path $shortcutPath) {
        Remove-Item $shortcutPath -Force
        Write-Host "Autostart removed:" $shortcutPath
    } else {
        Write-Host "Shortcut already missing:" $shortcutPath
    }
    exit 0
}

$WshShell = New-Object -ComObject WScript.Shell
$sc = $WshShell.CreateShortcut($shortcutPath)
$sc.TargetPath = $exe
$sc.Arguments = "`"$launcher`""
$sc.WorkingDirectory = $scriptDir
$sc.WindowStyle = 7   # 1=Normal, 7=Minimized
$sc.Description = "Evaluation UI localhost:9601"
$sc.Save()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null

Write-Host 'Autostart registered. Shortcut:' $shortcutPath
Write-Host 'From next logon http://localhost:9601/ starts automatically.'
Write-Host 'To remove: install_evaluation_ui_autostart.ps1 -Uninstall'
