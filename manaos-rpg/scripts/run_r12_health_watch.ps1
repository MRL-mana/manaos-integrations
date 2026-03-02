param(
	[string]$BaseUrl = 'http://127.0.0.1:9510',
	[int]$IntervalSec = 300,
	[int]$MaxLoops = 0,
	[switch]$Once,
	[switch]$FailOnError,
	[string]$JsonLogPath = '',
	[int]$MaxJsonLogSizeMB = 20,
	[int]$MaxJsonLogFiles = 5,
	[ValidateSet('generic','slack','discord')]
	[string]$WebhookFormat = 'discord',
	[string]$WebhookUrl = '',
	[string]$WebhookMention = '',
	[switch]$NotifyOnSuccess
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
		[int]$MaxSizeMB,
		[int]$MaxFiles,
		$Obj
	)
	if ([string]::IsNullOrWhiteSpace($Path)) { return }
	$dir = Split-Path -Parent $Path
	if ($dir -and -not (Test-Path $dir)) {
		New-Item -ItemType Directory -Force -Path $dir | Out-Null
	}

	if ($MaxSizeMB -gt 0 -and $MaxFiles -gt 0 -and (Test-Path $Path)) {
		$maxBytes = [int64]$MaxSizeMB * 1MB
		$currentBytes = (Get-Item $Path).Length
		if ($currentBytes -ge $maxBytes) {
			for ($index = $MaxFiles - 1; $index -ge 1; $index--) {
				$src = "$Path.$index"
				$dst = "$Path.$($index + 1)"
				if (Test-Path $src) {
					if ($index -eq $MaxFiles - 1) {
						Remove-Item -Force $src
					} else {
						Move-Item -Force $src $dst
					}
				}
			}
			Move-Item -Force $Path "$Path.1"
			Write-Host "[INFO] Rotated log: $Path" -ForegroundColor DarkGray
		}
	}

	($Obj | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Encoding UTF8 -Path $Path
}

function Resolve-NotifySettings {
	param(
		[string]$InWebhookUrl,
		[string]$InWebhookFormat,
		[string]$InWebhookMention,
		[bool]$InNotifyOnSuccess
	)

	$resolvedUrl = $InWebhookUrl
	if ([string]::IsNullOrWhiteSpace($resolvedUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
		$resolvedUrl = $env:MANAOS_WEBHOOK_URL
	}
	if ([string]::IsNullOrWhiteSpace($resolvedUrl)) {
		$resolvedUrl = [Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_URL', 'User')
	}

	$resolvedFormat = $InWebhookFormat
	if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_FORMAT)) {
		$envFormat = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
		if ($envFormat -in @('generic', 'slack', 'discord')) {
			$resolvedFormat = $envFormat
		}
	}

	$resolvedMention = $InWebhookMention
	if ([string]::IsNullOrWhiteSpace($resolvedMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
		$resolvedMention = $env:MANAOS_WEBHOOK_MENTION
	}

	$resolvedNotifyOnSuccess = $InNotifyOnSuccess
	if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
		$raw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
		$resolvedNotifyOnSuccess = ($raw -in @('1','true','yes','on'))
	}

	return [pscustomobject]@{
		webhook_url = [string]$resolvedUrl
		webhook_format = [string]$resolvedFormat
		webhook_mention = [string]$resolvedMention
		notify_on_success = [bool]$resolvedNotifyOnSuccess
	}
}

function Send-WebhookNotification {
	param(
		[string]$Url,
		[ValidateSet('generic','slack','discord')]
		[string]$Format,
		[string]$Status,
		[string]$Title,
		[string]$Body,
		[string]$Mention = ''
	)

	if ([string]::IsNullOrWhiteSpace($Url)) { return }

	$content = if ([string]::IsNullOrWhiteSpace($Mention)) { "$Title`n$Body" } else { "$Mention $Title`n$Body" }
	if ($Format -eq 'discord') {
		$payload = @{ content = $content }
	} elseif ($Format -eq 'slack') {
		$payload = @{ text = $content }
	} else {
		$payload = @{ status = $Status; title = $Title; body = $Body; mention = $Mention }
	}

	try {
		Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Depth 6) | Out-Null
		Write-Host "[OK] Webhook notified ($Status)" -ForegroundColor Green
	} catch {
		Write-Host "[WARN] Webhook notify failed: $($_.Exception.Message)" -ForegroundColor Yellow
	}
}

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success

$loop = 0
while ($true) {
	$loop++
	Write-Host "=== Round12 Health Watch (loop=$loop) ===" -ForegroundColor Yellow
	$res = Invoke-R12Check -Base $BaseUrl
	Write-JsonLine -Path $JsonLogPath -MaxSizeMB $MaxJsonLogSizeMB -MaxFiles $MaxJsonLogFiles -Obj $res

	$shouldNotify = ($res.failed -gt 0) -or ($NotifyOnSuccess -and $res.failed -eq 0)
	if ($shouldNotify -and -not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
		$status = if ($res.failed -gt 0) { 'failure' } else { 'success' }
		$title = if ($res.failed -gt 0) { '[R12 Watch] FAILURE' } else { '[R12 Watch] SUCCESS' }
		$failedEndpoints = @($res.details | Where-Object { -not $_.ok } | ForEach-Object { $_.endpoint })
		$detailLine = if ($failedEndpoints.Count -gt 0) { ('failed_endpoints=' + ($failedEndpoints -join ',')) } else { 'failed_endpoints=none' }
		$body = "base=$BaseUrl loop=$loop passed=$($res.passed) failed=$($res.failed) total=$($res.total) $detailLine"
		Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status $status -Title $title -Body $body -Mention $WebhookMention
	}

	if ($FailOnError.IsPresent -and $res.failed -gt 0) {
		throw "Round12 health check failed: $($res.failed) endpoint(s)"
	}

	if ($Once.IsPresent) { break }
	if ($MaxLoops -gt 0 -and $loop -ge $MaxLoops) { break }
	Start-Sleep -Seconds $IntervalSec
}
