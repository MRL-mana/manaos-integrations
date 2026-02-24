param(
  [string]$ServiceName = "ManaOSDockerStack",
  [string]$WorkingDir = (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\")).Path,
  [string]$ComposeFile = "",
  [string]$PowerShellExe = "powershell.exe",
  [string]$NssmExe = "",
  [switch]$StartNow,
  [switch]$RemoveOrphans
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsAdmin {
  return ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
  Write-Host "[INFO] Admin required. Relaunching elevated (UAC)..." -ForegroundColor Yellow
  $argList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $PSCommandPath
  ) + $MyInvocation.UnboundArguments
  $p = Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList -WorkingDirectory $PSScriptRoot -PassThru
  $p.WaitForExit()
  exit $p.ExitCode
}

function Ensure-Nssm {
  param([string]$Preferred)

  if (-not [string]::IsNullOrWhiteSpace($Preferred)) {
    if (Test-Path $Preferred) { return $Preferred }
    try {
      $cmd = Get-Command $Preferred -ErrorAction Stop
      if ($cmd -and $cmd.Source) { return $cmd.Source }
    } catch {
    }
  }

  $candidate = Join-Path $env:ProgramFiles "nssm\\nssm.exe"
  if (Test-Path $candidate) { return $candidate }

  try {
    $cmd = Get-Command nssm -ErrorAction Stop
    if ($cmd -and $cmd.Source) { return $cmd.Source }
  } catch {
  }

  Write-Host "[INFO] NSSM not found. Installing to $candidate ..." -ForegroundColor Yellow
  $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
  $zipPath = Join-Path $env:TEMP "nssm.zip"
  $extractDir = Join-Path $env:TEMP "nssm_extract"

  if (Test-Path $extractDir) {
    Remove-Item -Recurse -Force $extractDir -ErrorAction SilentlyContinue
  }

  Invoke-WebRequest -Uri $nssmUrl -OutFile $zipPath -UseBasicParsing
  Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

  $nssmExe = Get-ChildItem -Path $extractDir -Recurse -Filter "nssm.exe" |
    Where-Object { $_.DirectoryName -like "*win64*" } |
    Select-Object -First 1

  if (-not $nssmExe) {
    throw "Failed to locate nssm.exe in archive"
  }

  $targetDir = Split-Path $candidate -Parent
  New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
  Copy-Item -Force $nssmExe.FullName $candidate

  return $candidate
}

$NssmPath = Ensure-Nssm -Preferred $NssmExe

if ([string]::IsNullOrWhiteSpace($ComposeFile)) {
  $ComposeFile = Join-Path $WorkingDir "docker-compose.yml"
}

$Runner = Join-Path $WorkingDir "scripts\\windows\\run_manaos_docker_stack_service.ps1"
if (!(Test-Path $Runner)) {
  throw "Runner not found: $Runner"
}
if (!(Test-Path $ComposeFile)) {
  throw "Compose file not found: $ComposeFile"
}

Write-Host "Installing service: $ServiceName"
Write-Host "WorkingDir: $WorkingDir"
Write-Host "ComposeFile: $ComposeFile"
Write-Host "PowerShellExe: $PowerShellExe"
Write-Host "Runner: $Runner"

$appParams = "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`" -WorkingDir `"$WorkingDir`" -ComposeFile `"$ComposeFile`""
if ($RemoveOrphans) {
  $appParams += " -RemoveOrphans"
}

# Create service
& $NssmPath install $ServiceName $PowerShellExe $appParams
& $NssmPath set $ServiceName AppDirectory $WorkingDir
& $NssmPath set $ServiceName DisplayName "ManaOS Docker Stack"
& $NssmPath set $ServiceName Description "Runs ManaOS docker-compose stack and keeps it healthy"
& $NssmPath set $ServiceName Start SERVICE_AUTO_START
& $NssmPath set $ServiceName AppRestartDelay 5000
& $NssmPath set $ServiceName AppThrottle 1500

# Logs
$LogDir = Join-Path $WorkingDir "logs\\service"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
& $NssmPath set $ServiceName AppStdout (Join-Path $LogDir "docker_stack_stdout.log")
& $NssmPath set $ServiceName AppStderr (Join-Path $LogDir "docker_stack_stderr.log")
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateSeconds 86400

Write-Host "Installed. Start with: nssm start $ServiceName"

if ($StartNow) {
  & $NssmPath start $ServiceName
  Write-Host "Started: $ServiceName"
}
