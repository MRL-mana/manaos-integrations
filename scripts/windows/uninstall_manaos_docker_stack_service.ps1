param(
  [string]$ServiceName = "ManaOSDockerStack",
  [string]$NssmExe = ""
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

  throw "NSSM not found. Install it first (e.g. run install_manaos_docker_stack_service.ps1 once)."
}

$NssmPath = Ensure-Nssm -Preferred $NssmExe

Write-Host "Stopping service (if running): $ServiceName"
try {
  & $NssmPath stop $ServiceName | Out-Null
} catch {
}

Write-Host "Removing service: $ServiceName"
& $NssmPath remove $ServiceName confirm

Write-Host "Removed: $ServiceName"
