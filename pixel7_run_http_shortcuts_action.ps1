param(
    [string]$Serial = "100.84.2.125:5555",
    [string]$ActionLabelContains = "Remi Status",
    [string]$Package = "ch.rmy.android.http_shortcuts",
    [string]$WorkDir = "manaos_integrations",
    [string]$OutPrefix = "_tmp_http_shortcuts_action",
    [int]$WaitMs = 1400,
    [int]$MaxScrolls = 6,
    [int]$SwipeMs = 700,
    [int]$BackCount = 3
)

$ErrorActionPreference = "Stop"

function Dump-Ui([string]$remote, [string]$local) {
    adb -s $Serial shell uiautomator dump $remote | Out-Null
    adb -s $Serial pull $remote $local | Out-Null
}

function Get-FocusedPackage {
    try {
        $out = adb -s $Serial shell "dumpsys window | grep -E 'mCurrentFocus' | head -n 1" 2>$null
        if ($out -match 'mCurrentFocus=Window\{[^\s]+\s+u0\s+([^/]+)/') {
            return $Matches[1]
        }
    } catch {
        # ignore
    }
    return $null
}

# Launch app
adb -s $Serial shell monkey -p $Package -c android.intent.category.LAUNCHER 1 | Out-Null
Start-Sleep -Milliseconds 800

# HTTP Shortcuts tends to reopen the last response view (WebView/dialog).
# Probe UI first; only send Back if we're still inside HTTP Shortcuts and it looks like a response view.
$probeXmlPath = Join-Path $WorkDir ("{0}_probe.xml" -f $OutPrefix)
Dump-Ui /sdcard/_hs_probe.xml $probeXmlPath
$probeXml = Get-Content -Raw -Encoding UTF8 $probeXmlPath

$expectedPkgAttr = 'package="' + $Package + '"'
if ($probeXml -notmatch [regex]::Escape($expectedPkgAttr)) {
    $m = [regex]::Match($probeXml, 'package="([^"]+)"')
    $rootPkg = if ($m.Success) { $m.Groups[1].Value } else { "UNKNOWN" }
    Write-Host "NOT_IN_APP expected=$Package actual=$rootPkg"
    exit 3
}

for ($b = 0; $b -lt $BackCount; $b++) {
    $looksLikeResponse = (
        $probeXml -match 'android\.webkit\.WebView' -or
        $probeXml -match 'content-desc="閉じる"' -or
        $probeXml -match 'content-desc="共有する"'
    )
    if (-not $looksLikeResponse) { break }

    adb -s $Serial shell input keyevent 4 | Out-Null
    Start-Sleep -Milliseconds 250
    Dump-Ui /sdcard/_hs_probe.xml $probeXmlPath
    $probeXml = Get-Content -Raw -Encoding UTF8 $probeXmlPath
}

function Try-FindTapPoint([string]$xmlPath, [string]$textContains) {
    $json = python (Join-Path $WorkDir "extract_uia_bounds.py") $xmlPath --package $Package --text-contains $textContains --format json
    if ($null -eq $json) { return $null }
    $s = [string]$json
    if ($s.Trim() -eq "NOT_FOUND") { return $null }
    try {
        return ($s | ConvertFrom-Json)
    } catch {
        return $null
    }
}

$obj = $null
$matchedText = $null
$candidates = @()
$candidates += $ActionLabelContains
if ($ActionLabelContains -match '^Remi\s+') {
    $candidates += ($ActionLabelContains -replace '^Remi\s+','')
}
if ($ActionLabelContains -match '\s') {
    $candidates += (($ActionLabelContains -split '\s+') | Select-Object -Last 1)
}
$candidates = $candidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

$beforeXml = $null
for ($i = 0; $i -le $MaxScrolls; $i++) {
    $beforeXml = Join-Path $WorkDir ("{0}_before_s{1}.xml" -f $OutPrefix, $i)
    Dump-Ui /sdcard/_hs_before.xml $beforeXml

    foreach ($c in $candidates) {
        $obj = Try-FindTapPoint $beforeXml $c
        if ($null -ne $obj) {
            $matchedText = $c
            break
        }
    }
    if ($null -ne $obj) { break }

    if ($i -lt $MaxScrolls) {
        # Scroll down the list to reveal more actions.
        adb -s $Serial shell input swipe 520 1650 520 450 $SwipeMs | Out-Null
        Start-Sleep -Milliseconds 450
    }
}

if ($null -eq $obj) {
    Write-Host "NOT_FOUND label=$ActionLabelContains"
    exit 2
}

$x = [int]$obj.bounds.center.x
$y = [int]$obj.bounds.center.y
Write-Host ("TAP {0},{1} ({2}) label={3} matched={4}" -f $x, $y, $obj.bounds.raw, $ActionLabelContains, $matchedText)

adb -s $Serial shell input tap $x $y | Out-Null
Start-Sleep -Milliseconds $WaitMs

$afterXml = Join-Path $WorkDir ("{0}_after.xml" -f $OutPrefix)
Dump-Ui /sdcard/_hs_after.xml $afterXml

$afterPng = Join-Path $WorkDir ("{0}_after.png" -f $OutPrefix)
adb -s $Serial shell screencap -p /sdcard/_hs_after.png
adb -s $Serial pull /sdcard/_hs_after.png $afterPng | Out-Null

Write-Host "SAVED_XML $afterXml"
Write-Host "SAVED_PNG $afterPng"

$failHit = Select-String -Path $afterXml -Pattern 'failed|connect|timeout|ERR_' -CaseSensitive:$false -Quiet
Write-Host ("FAIL_KEYWORDS_FOUND={0}" -f $failHit)
