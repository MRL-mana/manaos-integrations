param(
  [string]$TaskName = "ManaOS_DockerStack",
  [ValidateSet("Logon","Startup")]
  [string]$Trigger = "Logon",
  [string]$WorkingDir = (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\")).Path,
  [string]$ComposeFile = "",
  [ValidateSet("Limited","Highest")]
  [string]$RunLevel = "Limited",
  [switch]$Elevate,
  [switch]$RemoveOrphans,
  [switch]$NoWindow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Normalize-DirArg {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) {
    return $Path
  }

  $p = $Path.Trim()
  if ($p -match '^[A-Za-z]:\\$') {
    return $p
  }

  return $p.TrimEnd('\', '/')
}

function Test-IsAdmin {
  try {
    return ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  } catch {
    return $false
  }
}

if ($Elevate -and -not (Test-IsAdmin)) {
  Write-Host "[INFO] Elevation requested. Relaunching elevated (UAC)..." -ForegroundColor Yellow
  $argList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $PSCommandPath
  ) + $MyInvocation.UnboundArguments
  $p = Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList -WorkingDirectory $PSScriptRoot -PassThru
  $p.WaitForExit()
  exit $p.ExitCode
}

function Install-RunKeyFallback {
  param(
    [Parameter(Mandatory = $true)][string]$EntryName,
    [Parameter(Mandatory = $true)][string]$WorkingDir,
    [Parameter(Mandatory = $true)][string]$ComposeFile,
    [switch]$RemoveOrphans
  )

  $WorkingDirArg = Normalize-DirArg -Path $WorkingDir

  $psExe = "$env:WINDIR\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
  if (-not (Test-Path $psExe)) {
    $psExe = "powershell.exe"
  }

  $runner = Join-Path $WorkingDir "scripts\\windows\\run_manaos_docker_stack_service.ps1"

  $cmd = '"' + $psExe + '"' +
    ' -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden' +
    ' -File ' + ('"' + $runner + '"') +
    ' -WorkingDir ' + ('"' + $WorkingDirArg + '"') +
    ' -ComposeFile ' + ('"' + $ComposeFile + '"')

  if ($RemoveOrphans) {
    $cmd += ' -RemoveOrphans'
  }

  $runKey = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
  if (-not (Test-Path $runKey)) {
    New-Item -Path $runKey -Force | Out-Null
  }

  Set-ItemProperty -Path $runKey -Name $EntryName -Value $cmd -Type String
  Write-Host "[OK] Fallback applied: HKCU Run entry set: $EntryName" -ForegroundColor Green
}

if ([string]::IsNullOrWhiteSpace($ComposeFile)) {
  $ComposeFile = Join-Path $WorkingDir "docker-compose.yml"
}

$WorkingDirArg = Normalize-DirArg -Path $WorkingDir

$Runner = Join-Path $WorkingDir "scripts\\windows\\run_manaos_docker_stack_service.ps1"
if (!(Test-Path $Runner)) {
  throw "Runner not found: $Runner"
}
if (!(Test-Path $ComposeFile)) {
  throw "Compose file not found: $ComposeFile"
}

$psExe = "$env:WINDIR\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
if (-not (Test-Path $psExe)) {
  $psExe = "powershell.exe"
}

$taskArgs = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-WindowStyle", "Hidden"
)
$taskArgs += @(
  "-File", ('"' + $Runner + '"'),
  "-WorkingDir", ('"' + $WorkingDirArg + '"'),
  "-ComposeFile", ('"' + $ComposeFile + '"')
)
if ($RemoveOrphans) {
  $taskArgs += "-RemoveOrphans"
}

$action = New-ScheduledTaskAction -Execute $psExe -Argument ($taskArgs -join ' ') -WorkingDirectory $WorkingDirArg

$triggerObj = if ($Trigger -eq "Startup") {
  New-ScheduledTaskTrigger -AtStartup
} else {
  New-ScheduledTaskTrigger -AtLogOn
}

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel $RunLevel
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -Hidden

try {
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggerObj -Principal $principal -Settings $settings -Description "Auto-start ManaOS docker-compose stack" -Force | Out-Null
  Write-Host "[OK] Task registered: $TaskName (Trigger=$Trigger)" -ForegroundColor Green
  Write-Host "Start now: Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Cyan
  Write-Host "Delete:   Unregister-ScheduledTask -TaskName $TaskName -Confirm:\$false" -ForegroundColor Cyan

  # If we previously fell back to HKCU Run, remove it to prevent double-start.
  $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
  try {
    if (Test-Path $runKey) {
      Remove-ItemProperty -Path $runKey -Name $TaskName -ErrorAction SilentlyContinue
      Write-Host "[OK] Run entry removed (if existed): $TaskName" -ForegroundColor Green
    }
  } catch {
    Write-Host "[WARN] Failed to remove Run entry: $TaskName" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor DarkGray
  }
}
catch {
  Write-Host "[WARN] Failed to register scheduled task: $($_.Exception.Message)" -ForegroundColor Yellow
  Write-Host "[INFO] Falling back to HKCU Run entry (no-admin autostart)..." -ForegroundColor Gray
  Install-RunKeyFallback -EntryName $TaskName -WorkingDir $WorkingDir -ComposeFile $ComposeFile -RemoveOrphans:$RemoveOrphans
}
