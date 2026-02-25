param(
    [ValidateSet('Auto','Day','Night')]
    [string]$Profile = 'Auto',
    [ValidateSet('Auto','Weekday','Weekend')]
    [string]$WeekType = 'Auto',
    [switch]$EnableWeeklyThresholdProfile,
    [switch]$EnableHolidayAsWeekend,
    [string]$HolidayDateFile = '',
    [ValidateSet('NightAlways','NightWeekendOnly')]
    [string]$RebootRecoveryMode = 'NightAlways',
    [switch]$RemoteOnly,
    [switch]$NotifyOnRecover,
    [string]$PixelHost = '',
    [int]$ApiPort = 0,
    [string]$DeviceSerial = '',
    [int]$DayStartHour = 7,
    [int]$NightStartHour = 22,
    [int]$WeekdayDegradedAfterFailures = 2,
    [int]$WeekdayStrongRecoverAfterFailures = 5,
    [int]$WeekdayRebootTestAfterFailures = 8,
    [int]$WeekendDegradedAfterFailures = 3,
    [int]$WeekendStrongRecoverAfterFailures = 6,
    [int]$WeekendRebootTestAfterFailures = 10
)

$ErrorActionPreference = 'Stop'

function Resolve-Profile([string]$Requested, [int]$DayHour, [int]$NightHour) {
    if ($Requested -eq 'Day' -or $Requested -eq 'Night') {
        return $Requested
    }

    $h = (Get-Date).Hour
    if ($DayHour -lt 0) { $DayHour = 0 }
    if ($DayHour -gt 23) { $DayHour = 23 }
    if ($NightHour -lt 0) { $NightHour = 0 }
    if ($NightHour -gt 23) { $NightHour = 23 }

    if ($DayHour -eq $NightHour) {
        return 'Day'
    }

    if ($DayHour -lt $NightHour) {
        if ($h -ge $DayHour -and $h -lt $NightHour) { return 'Day' }
        return 'Night'
    }

    if ($h -ge $DayHour -or $h -lt $NightHour) { return 'Day' }
    return 'Night'
}

function Resolve-WeekType([string]$Requested) {
    if ($Requested -eq 'Weekday' -or $Requested -eq 'Weekend') {
        return $Requested
    }

    $dow = (Get-Date).DayOfWeek
    if ($dow -eq [System.DayOfWeek]::Saturday -or $dow -eq [System.DayOfWeek]::Sunday) {
        return 'Weekend'
    }
    return 'Weekday'
}

function Resolve-HolidayDateSet([string]$Path) {
    $set = New-Object 'System.Collections.Generic.HashSet[string]'
    if ([string]::IsNullOrWhiteSpace($Path)) { return $set }
    if (-not (Test-Path $Path)) { return $set }

    $lines = Get-Content -Encoding UTF8 $Path -ErrorAction SilentlyContinue
    foreach ($raw in $lines) {
        $line = [string]$raw
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $line = $line.Trim()
        if ($line.StartsWith('#')) { continue }
        if ($line -match '^\d{4}-\d{2}-\d{2}$') {
            $null = $set.Add($line)
        }
    }
    return $set
}

function Get-TodayDateKey {
    return (Get-Date).ToString('yyyy-MM-dd')
}

function Clamp-Int([int]$Value, [int]$Min, [int]$Max) {
    if ($Value -lt $Min) { return $Min }
    if ($Value -gt $Max) { return $Max }
    return $Value
}

$root = $PSScriptRoot
$startScript = Join-Path $root 'pixel7_edge_watch_start.ps1'
if (-not (Test-Path $startScript)) { throw "not found: $startScript" }

if ([string]::IsNullOrWhiteSpace($HolidayDateFile)) {
    $HolidayDateFile = Join-Path $root 'config\pixel7_holidays_jp.txt'
}

$resolved = Resolve-Profile -Requested $Profile -DayHour $DayStartHour -NightHour $NightStartHour
$resolvedWeekType = Resolve-WeekType -Requested $WeekType
$todayKey = Get-TodayDateKey
$holidaySet = Resolve-HolidayDateSet -Path $HolidayDateFile
$isHoliday = $false
if ($EnableHolidayAsWeekend -and $resolvedWeekType -eq 'Weekday') {
    if ($holidaySet.Contains($todayKey)) {
        $resolvedWeekType = 'Weekend'
        $isHoliday = $true
    }
}

$degradedAfter = 2
$strongAfter = 5
$rebootAfter = 8

if ($EnableWeeklyThresholdProfile) {
    if ($resolvedWeekType -eq 'Weekend') {
        $degradedAfter = $WeekendDegradedAfterFailures
        $strongAfter = $WeekendStrongRecoverAfterFailures
        $rebootAfter = $WeekendRebootTestAfterFailures
    }
    else {
        $degradedAfter = $WeekdayDegradedAfterFailures
        $strongAfter = $WeekdayStrongRecoverAfterFailures
        $rebootAfter = $WeekdayRebootTestAfterFailures
    }
}

$degradedAfter = Clamp-Int -Value $degradedAfter -Min 1 -Max 20
$strongAfter = Clamp-Int -Value $strongAfter -Min $degradedAfter -Max 30
$rebootAfter = Clamp-Int -Value $rebootAfter -Min $strongAfter -Max 50

$startArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $startScript,
    '-IntervalSeconds', '300',
    '-DegradedIntervalSeconds', '60',
    '-DegradedAfterFailures', [string]$degradedAfter,
    '-StrongRecoverAfterFailures', [string]$strongAfter,
    '-StrongRecoverCooldownSec', '600',
    '-RebootTestAfterFailures', [string]$rebootAfter,
    '-RebootTestCooldownSec', '3600',
    '-FailureNotifyCooldownSec', '900',
    '-ForcedGatewayRecoverCooldownSec', '300',
    '-AutoRecoverOnFailure'
)

if ($NotifyOnRecover) { $startArgs += '-NotifyOnRecover' }
if ($RemoteOnly) { $startArgs += '-RemoteOnly' }
if ($PixelHost) { $startArgs += @('-PixelHost', $PixelHost) }
if ($ApiPort -gt 0) { $startArgs += @('-ApiPort', [string]$ApiPort) }
if ($DeviceSerial) { $startArgs += @('-DeviceSerial', $DeviceSerial) }

$enableRebootRecovery = $false
if ($resolved -eq 'Night') {
    if ($RebootRecoveryMode -eq 'NightAlways') {
        $enableRebootRecovery = $true
    }
    elseif ($resolvedWeekType -eq 'Weekend') {
        $enableRebootRecovery = $true
    }
}

if ($enableRebootRecovery) {
    $startArgs += '-EnableRebootTestRecovery'
}

Write-Host ("profile={0} requested={1} weekType={2} holiday={3} holidayAsWeekend={4} weeklyThresholds={5} rebootMode={6} hour={7} remoteOnly={8} rebootRecovery={9} thresholds={10}/{11}/{12}" -f $resolved, $Profile, $resolvedWeekType, $isHoliday, [bool]$EnableHolidayAsWeekend, [bool]$EnableWeeklyThresholdProfile, $RebootRecoveryMode, (Get-Date).Hour, [bool]$RemoteOnly, $enableRebootRecovery, $degradedAfter, $strongAfter, $rebootAfter) -ForegroundColor Cyan

& pwsh @startArgs
exit $LASTEXITCODE
