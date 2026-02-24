param(
  [string]$Serial = "39111JEHN00394",
  [string]$Uri = "content://com.android.externalstorage.documents/document/primary:Download/remi_android_shortcuts.json"
)

$ErrorActionPreference = "SilentlyContinue"

Write-Host "Checking HTTP Shortcuts focus..." -ForegroundColor Cyan
adb start-server | Out-Null

adb -s $Serial shell am start -a android.intent.action.SEND -t application/json --grant-read-uri-permission --eu android.intent.extra.STREAM $Uri -n ch.rmy.android.http_shortcuts/.activities.misc.share.ShareActivity | Out-Null
Start-Sleep -Milliseconds 800

$remote = "/data/local/tmp/_hs_check.xml"
$local = Join-Path $PSScriptRoot "_tmp_hs_check.xml"
adb -s $Serial shell uiautomator dump $remote | Out-Null
adb -s $Serial pull $remote $local | Out-Null

$xml = ""
try { $xml = Get-Content -Raw -Encoding UTF8 $local } catch { $xml = "" }

$rootPkg = "UNKNOWN"
if ($xml -match 'package="([^"]+)"') {
  $rootPkg = $Matches[1]
}

$focused = $false
if ($xml -match 'package="ch\.rmy\.android\.http_shortcuts"') {
  $focused = $true
}

Write-Host ("root_package={0}" -f $rootPkg) -ForegroundColor Gray
Write-Host ("FOCUSED_HTTP_SHORTCUTS={0}" -f $focused) -ForegroundColor Yellow
Write-Host ("dump={0}" -f $local) -ForegroundColor Gray

if ($focused) { exit 0 }
exit 2
