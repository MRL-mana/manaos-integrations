param(
  [string]$TaskName = "ManaOS_DockerStack",
  [switch]$Elevate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

try {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
} catch {
}

try {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop | Out-Null
  Write-Host "[OK] Task removed: $TaskName" -ForegroundColor Green
} catch {
  Write-Host "[WARN] Task not found or failed to remove: $TaskName" -ForegroundColor Yellow
  Write-Host $_.Exception.Message -ForegroundColor DarkGray
}

# Also remove Run-key fallback (if present)
$runKey = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
try {
  if (Test-Path $runKey) {
    Remove-ItemProperty -Path $runKey -Name $TaskName -ErrorAction SilentlyContinue
    Write-Host "[OK] Run entry removed (if existed): $TaskName" -ForegroundColor Green
  }
} catch {
  Write-Host "[WARN] Failed to remove Run entry: $TaskName" -ForegroundColor Yellow
  Write-Host $_.Exception.Message -ForegroundColor DarkGray
}
