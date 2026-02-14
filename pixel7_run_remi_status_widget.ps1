param(
    [string]$Serial = "100.84.2.125:5555",
    [string]$LabelContains = "Remi Status",
    [string]$WidgetPackage = "ch.rmy.android.http_shortcuts",
    [int]$MaxLeft = 8,
    [int]$MaxRight = 16,
    [string]$WorkDir = "manaos_integrations",
    [string]$OutPrefix = "_tmp_remi_widget"
)

$ErrorActionPreference = "Stop"

function Dump-Home([string]$dst) {
    adb -s $Serial shell uiautomator dump /sdcard/_home.xml | Out-Null
    adb -s $Serial pull /sdcard/_home.xml $dst | Out-Null
}

function Swipe-Left() {
    adb -s $Serial shell input swipe 850 1200 250 1200 250 | Out-Null
    Start-Sleep -Milliseconds 350
}

function Swipe-Right() {
    adb -s $Serial shell input swipe 250 1200 850 1200 250 | Out-Null
    Start-Sleep -Milliseconds 350
}

adb -s $Serial shell input keyevent KEYCODE_HOME | Out-Null
Start-Sleep -Milliseconds 500

$foundFile = $null

for ($i = 1; $i -le $MaxLeft; $i++) {
    $dst = Join-Path $WorkDir ("{0}_home_L_{1}.xml" -f $OutPrefix, $i)
    Dump-Home $dst
    $hit = Select-String -Path $dst -Pattern ([Regex]::Escape($WidgetPackage)) -CaseSensitive:$false -Quiet
    Write-Host ("LEFT {0} hit={1}" -f $i, $hit)
    if ($hit) { $foundFile = $dst; break }
    Swipe-Left
}

if (-not $foundFile) {
    for ($i = 1; $i -le $MaxRight; $i++) {
        $dst = Join-Path $WorkDir ("{0}_home_R_{1}.xml" -f $OutPrefix, $i)
        Dump-Home $dst
        $hit = Select-String -Path $dst -Pattern ([Regex]::Escape($WidgetPackage)) -CaseSensitive:$false -Quiet
        Write-Host ("RIGHT {0} hit={1}" -f $i, $hit)
        if ($hit) { $foundFile = $dst; break }
        Swipe-Right
    }
}

if (-not $foundFile) {
    throw "Widget not found in home scan. package=$WidgetPackage label~=$LabelContains"
}

Write-Host "FOUND_IN $foundFile"

$json = python (Join-Path $WorkDir "extract_uia_bounds.py") $foundFile --package $WidgetPackage --text-contains $LabelContains --format json
$obj = $json | ConvertFrom-Json
$x = [int]$obj.bounds.center.x
$y = [int]$obj.bounds.center.y
Write-Host ("TAP {0},{1} ({2}) label={3}" -f $x, $y, $obj.bounds.raw, $LabelContains)

adb -s $Serial shell input tap $x $y | Out-Null
Start-Sleep -Milliseconds 1200

$afterXml = Join-Path $WorkDir ("{0}_after.xml" -f $OutPrefix)
adb -s $Serial shell uiautomator dump /sdcard/_after.xml | Out-Null
adb -s $Serial pull /sdcard/_after.xml $afterXml | Out-Null

$afterPng = Join-Path $WorkDir ("{0}_after.png" -f $OutPrefix)
adb -s $Serial shell screencap -p /sdcard/_after.png
adb -s $Serial pull /sdcard/_after.png $afterPng | Out-Null

Write-Host "SAVED_XML $afterXml"
Write-Host "SAVED_PNG $afterPng"

$failHit = Select-String -Path $afterXml -Pattern 'failed|connect|timeout|ERR_' -CaseSensitive:$false -Quiet
Write-Host ("FAIL_KEYWORDS_FOUND={0}" -f $failHit)
