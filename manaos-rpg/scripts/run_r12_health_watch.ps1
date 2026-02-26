param(
	[string]$BaseUrl = 'http://127.0.0.1:9510',
	[int]$IntervalSec = 300,
	[int]$MaxLoops = 0,
	[switch]$Once,
	[switch]$FailOnError,
	[string]$JsonLogPath = ''
)

$ErrorActionPreference = 'Stop'

$endpoints = @(
	'/health',
	'/api/rl/r12/summary',
	'/api/rl/r12/recommendations',
	'/api/rl/causal/stats'
)

function Invoke-R12Check {
	param([string]$Base)

	$ok = 0
	$ng = 0
	$details = @()

	foreach ($ep in $endpoints) {
		$url = "$Base$ep"
		try {
			$r = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 8
			$success = ($ep -eq '/health') -or [bool]$r.ok
			if ($success) {
				$ok++
				$details += [pscustomobject]@{ endpoint = $ep; ok = $true; error = $null }
				Write-Host "[PASS] GET $ep" -ForegroundColor Green
			} else {
				$ng++
				$err = [string]($r.error)
				$details += [pscustomobject]@{ endpoint = $ep; ok = $false; error = $err }
				Write-Host "[FAIL] GET $ep -> $err" -ForegroundColor Red
			}
		} catch {
			$ng++
			$err = [string]$_.Exception.Message
			$details += [pscustomobject]@{ endpoint = $ep; ok = $false; error = $err }
			Write-Host "[FAIL] GET $ep -> $err" -ForegroundColor Red
		}
	}

	$result = [pscustomobject]@{
		ts = [DateTimeOffset]::Now.ToString('o')
		base_url = $Base
		total = $endpoints.Count
		passed = $ok
		failed = $ng
		details = $details
	}

	Write-Host ("R12 Watch: {0} passed, {1} failed / {2}" -f $ok, $ng, $endpoints.Count) -ForegroundColor Cyan
	return $result
}

function Write-JsonLine {
	param(
		[string]$Path,
		$Obj
	)
	if ([string]::IsNullOrWhiteSpace($Path)) { return }
	$dir = Split-Path -Parent $Path
	if ($dir -and -not (Test-Path $dir)) {
		New-Item -ItemType Directory -Force -Path $dir | Out-Null
	}
	($Obj | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Encoding UTF8 -Path $Path
}

$loop = 0
while ($true) {
	$loop++
	Write-Host "=== Round12 Health Watch (loop=$loop) ===" -ForegroundColor Yellow
	$res = Invoke-R12Check -Base $BaseUrl
	Write-JsonLine -Path $JsonLogPath -Obj $res

	if ($FailOnError.IsPresent -and $res.failed -gt 0) {
		throw "Round12 health check failed: $($res.failed) endpoint(s)"
	}

	if ($Once.IsPresent) { break }
	if ($MaxLoops -gt 0 -and $loop -ge $MaxLoops) { break }
	Start-Sleep -Seconds $IntervalSec
}
