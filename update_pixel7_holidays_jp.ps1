param(
    [int[]]$Years,
    [switch]$IncludeNextYear,
    [string]$OutFile = "",
    [switch]$PrintOnly
)

$ErrorActionPreference = 'Stop'

function Get-NthWeekdayOfMonth {
    param(
        [int]$Year,
        [int]$Month,
        [System.DayOfWeek]$Weekday,
        [int]$Nth
    )

    $first = [datetime]::new($Year, $Month, 1)
    $offset = (([int]$Weekday - [int]$first.DayOfWeek) + 7) % 7
    $day = 1 + $offset + (7 * ($Nth - 1))
    return [datetime]::new($Year, $Month, $day)
}

function Get-VernalEquinoxDay {
    param([int]$Year)
    $v = [math]::Floor(20.8431 + 0.242194 * ($Year - 1980) - [math]::Floor(($Year - 1980) / 4))
    return [int]$v
}

function Get-AutumnEquinoxDay {
    param([int]$Year)
    $v = [math]::Floor(23.2488 + 0.242194 * ($Year - 1980) - [math]::Floor(($Year - 1980) / 4))
    return [int]$v
}

function Add-Holiday {
    param(
        [hashtable]$Map,
        [datetime]$Date,
        [string]$Name
    )
    $k = $Date.ToString('yyyy-MM-dd')
    if (-not $Map.ContainsKey($k)) {
        $Map[$k] = $Name
    }
}

function Build-JpHolidayMap {
    param([int]$Year)

    $map = @{}

    Add-Holiday -Map $map -Date ([datetime]::new($Year, 1, 1)) -Name '元日'
    Add-Holiday -Map $map -Date (Get-NthWeekdayOfMonth -Year $Year -Month 1 -Weekday ([System.DayOfWeek]::Monday) -Nth 2) -Name '成人の日'
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 2, 11)) -Name '建国記念の日'
    if ($Year -ge 2020) {
        Add-Holiday -Map $map -Date ([datetime]::new($Year, 2, 23)) -Name '天皇誕生日'
    }
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 3, (Get-VernalEquinoxDay -Year $Year))) -Name '春分の日'
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 4, 29)) -Name '昭和の日'
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 5, 3)) -Name '憲法記念日'
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 5, 4)) -Name 'みどりの日'
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 5, 5)) -Name 'こどもの日'
    Add-Holiday -Map $map -Date (Get-NthWeekdayOfMonth -Year $Year -Month 7 -Weekday ([System.DayOfWeek]::Monday) -Nth 3) -Name '海の日'
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 8, 11)) -Name '山の日'
    Add-Holiday -Map $map -Date (Get-NthWeekdayOfMonth -Year $Year -Month 9 -Weekday ([System.DayOfWeek]::Monday) -Nth 3) -Name '敬老の日'
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 9, (Get-AutumnEquinoxDay -Year $Year))) -Name '秋分の日'
    Add-Holiday -Map $map -Date (Get-NthWeekdayOfMonth -Year $Year -Month 10 -Weekday ([System.DayOfWeek]::Monday) -Nth 2) -Name 'スポーツの日'
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 11, 3)) -Name '文化の日'
    Add-Holiday -Map $map -Date ([datetime]::new($Year, 11, 23)) -Name '勤労感謝の日'

    $changed = $true
    while ($changed) {
        $changed = $false

        $keys = @($map.Keys | Sort-Object)
        foreach ($k in $keys) {
            $d = [datetime]::ParseExact($k, 'yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture)
            if ($d.DayOfWeek -ne [System.DayOfWeek]::Sunday) { continue }

            $sub = $d.AddDays(1)
            while ($sub.Year -eq $Year) {
                $sk = $sub.ToString('yyyy-MM-dd')
                if (-not $map.ContainsKey($sk)) {
                    $map[$sk] = '振替休日'
                    $changed = $true
                    break
                }
                $sub = $sub.AddDays(1)
            }
        }

        $ordered = @($map.Keys | Sort-Object)
        for ($i = 0; $i -lt $ordered.Count - 1; $i++) {
            $d1 = [datetime]::ParseExact($ordered[$i], 'yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture)
            $d2 = [datetime]::ParseExact($ordered[$i + 1], 'yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture)
            if (($d2 - $d1).Days -ne 2) { continue }

            $mid = $d1.AddDays(1)
            if ($mid.DayOfWeek -eq [System.DayOfWeek]::Sunday) { continue }
            if ($mid.Year -ne $Year) { continue }

            $mk = $mid.ToString('yyyy-MM-dd')
            if (-not $map.ContainsKey($mk)) {
                $map[$mk] = '国民の休日'
                $changed = $true
            }
        }
    }

    return $map
}

$nowYear = (Get-Date).Year
if (-not $Years -or $Years.Count -eq 0) {
    $Years = @($nowYear)
    if ($IncludeNextYear) {
        $Years += ($nowYear + 1)
    }
}

$Years = @($Years | Sort-Object -Unique)

$allDates = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($year in $Years) {
    if ($year -lt 2000 -or $year -gt 2099) {
        throw "Year out of supported range (2000-2099): $year"
    }
    $m = Build-JpHolidayMap -Year $year
    foreach ($k in $m.Keys) {
        $null = $allDates.Add($k)
    }
}

$sorted = @($allDates | Sort-Object)

if ($PrintOnly) {
    $sorted | Out-Host
    exit 0
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
    $OutFile = Join-Path $PSScriptRoot 'config\pixel7_holidays_jp.txt'
}

$outDir = Split-Path -Parent $OutFile
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

$lines = @(
    '# Pixel7 半自律監視: 祝日リスト（yyyy-MM-dd）',
    '# Auto-generated by update_pixel7_holidays_jp.ps1',
    ('# GeneratedAt: {0}' -f (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')),
    ('# Years: {0}' -f ($Years -join ', ')),
    ''
) + $sorted

Set-Content -Encoding UTF8 -Path $OutFile -Value $lines

Write-Host ('updated: {0}' -f $OutFile) -ForegroundColor Green
Write-Host ('dates  : {0}' -f $sorted.Count) -ForegroundColor Green
Write-Host ('years  : {0}' -f ($Years -join ', ')) -ForegroundColor DarkGray
