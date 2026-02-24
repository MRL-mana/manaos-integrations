param(
  [int]$X = 20,
  [int]$Y = 20,
  [int]$Width = 1200,
  [int]$Height = 920,
  [switch]$Maximize
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$p = Get-Process scrcpy -ErrorAction SilentlyContinue | Sort-Object StartTime -Descending | Select-Object -First 1
if (-not $p) {
  Write-Host 'scrcpy process not found' -ForegroundColor Yellow
  exit 2
}

$hwnd = [IntPtr]$p.MainWindowHandle
Write-Host ("scrcpy pid={0} title={1} hwnd={2}" -f $p.Id, $p.MainWindowTitle, $p.MainWindowHandle) -ForegroundColor Gray

if ($hwnd -eq [IntPtr]::Zero) {
  Write-Host 'scrcpy has no main window handle yet (wait a moment and retry)' -ForegroundColor Yellow
  exit 3
}

try {
  $ws = New-Object -ComObject WScript.Shell
  $null = $ws.AppActivate($p.Id)
} catch {}

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WinScrcpy {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
}
"@ -ErrorAction SilentlyContinue | Out-Null

# 9=restore, 3=maximize
[WinScrcpy]::ShowWindowAsync($hwnd, 9) | Out-Null
Start-Sleep -Milliseconds 80
if ($Maximize) {
  [WinScrcpy]::ShowWindowAsync($hwnd, 3) | Out-Null
} else {
  [WinScrcpy]::MoveWindow($hwnd, $X, $Y, $Width, $Height, $true) | Out-Null
}
Start-Sleep -Milliseconds 80
[WinScrcpy]::SetForegroundWindow($hwnd) | Out-Null

Write-Host 'OK' -ForegroundColor Green
exit 0
