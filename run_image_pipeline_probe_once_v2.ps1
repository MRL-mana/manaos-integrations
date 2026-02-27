param(
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$probeScript = Join-Path $scriptDir "monitor_image_pipeline.ps1"
if (-not (Test-Path $probeScript)) { throw "Probe script not found: $probeScript" }
if ([string]::IsNullOrWhiteSpace($ConfigFile)) { $ConfigFile = Join-Path $scriptDir "logs\image_pipeline_probe_task.config.json" }

$unifiedApiUrl = "http://127.0.0.1:9502"
$comfyUiUrl = "http://127.0.0.1:8188"
$logFile = Join-Path $scriptDir "logs\image_pipeline_probe.latest.json"
$historyFile = Join-Path $scriptDir "logs\image_pipeline_probe.history.jsonl"
$stateFile = Join-Path $scriptDir "logs\image_pipeline_probe.state.json"
$webhookUrl = ""
$webhookFormat = "discord"
$webhookMention = ""
$notifyOnSuccess = $false
$notifyOnRecovery = $true
$notifyOnPartial = $true
$notifyOnDown = $true
$notifyCooldownMinutes = 15
$notifyStateFile = Join-Path $scriptDir "logs\image_pipeline_probe_notify_state.json"
$enableAutoRecovery = $false
$recoverAfterConsecutiveDown = 3
$recoveryCooldownSec = 300
$recoveryCommand = ""

function Ensure-ParentDir([string]$Path) { $dir = Split-Path -Parent $Path; if (-not [string]::IsNullOrWhiteSpace($dir) -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null } }
function To-Bool([object]$Value,[bool]$Default=$false){ if($null -eq $Value){return $Default}; if($Value -is [bool]){return [bool]$Value}; $v=([string]$Value).Trim().ToLowerInvariant(); if($v -in @('1','true','yes','on','enabled')){return $true}; if($v -in @('0','false','no','off','disabled')){return $false}; return $Default }
function Load-NotifyState([string]$Path){ if(-not (Test-Path $Path)){ return [pscustomobject]@{last_status='';last_notified_at='';last_category=''} }; try { return (Get-Content -Path $Path -Raw | ConvertFrom-Json) } catch { return [pscustomobject]@{last_status='';last_notified_at='';last_category=''} } }
function Save-NotifyState([string]$Path,[string]$Status,[string]$Category,[switch]$MarkNotified){ Ensure-ParentDir -Path $Path; $obj=[ordered]@{last_status=$Status;last_category=$Category;updated_at=[datetimeoffset]::Now.ToString('o')}; if($MarkNotified){$obj.last_notified_at=[datetimeoffset]::Now.ToString('o')} else {$obj.last_notified_at=[string](Load-NotifyState -Path $Path).last_notified_at}; ($obj|ConvertTo-Json -Depth 4)|Set-Content -Path $Path -Encoding UTF8 }
function Load-PipelineState([string]$Path){ if(-not (Test-Path $Path)){ return [pscustomobject]@{last_category='';consecutive_down=0;last_recovery_at=''} }; try { return (Get-Content -Path $Path -Raw | ConvertFrom-Json) } catch { return [pscustomobject]@{last_category='';consecutive_down=0;last_recovery_at=''} } }
function Save-PipelineState([string]$Path,[string]$Category,[int]$ConsecutiveDown,[string]$LastRecoveryAt){ Ensure-ParentDir -Path $Path; $obj=[ordered]@{last_category=$Category;consecutive_down=$ConsecutiveDown;last_recovery_at=$LastRecoveryAt;updated_at=[datetimeoffset]::Now.ToString('o')}; ($obj|ConvertTo-Json -Depth 4)|Set-Content -Path $Path -Encoding UTF8 }
function Append-ProbeHistory([string]$Path,[object]$Entry){ Ensure-ParentDir -Path $Path; ($Entry|ConvertTo-Json -Depth 16 -Compress) | Add-Content -Path $Path -Encoding UTF8 }
function Send-WebhookNotification([string]$Url,[string]$Format,[string]$Status,[string]$Title,[string]$Body,[string]$Mention=''){ if([string]::IsNullOrWhiteSpace($Url)){return}; $content = if([string]::IsNullOrWhiteSpace($Mention)){"$Title`n$Body"}else{"$Mention $Title`n$Body"}; if($Format -eq 'discord'){ $payload=@{content=$content} } elseif($Format -eq 'slack'){ $payload=@{text=$content} } else { $payload=@{status=$Status;title=$Title;body=$Body;mention=$Mention} }; try { Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json' -Body ($payload|ConvertTo-Json -Depth 8) | Out-Null } catch { Write-Host "[WARN] Webhook notify failed: $($_.Exception.Message)" -ForegroundColor Yellow } }
function Try-RecoverUnifiedApi([string]$UnifiedApiBaseUrl,[string]$CommandText){ $outcome=[ordered]@{attempted=$true;stopped_pid=$null;started=$false;command=$CommandText;error=$null}; try { $uri=[System.Uri]$UnifiedApiBaseUrl; $port=[int]$uri.Port; $conn=Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if($conn){ $pid=[int]$conn.OwningProcess; Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue; $outcome.stopped_pid=$pid; Start-Sleep -Milliseconds 500 }; Start-Process -FilePath "pwsh" -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-Command",$CommandText) -WindowStyle Hidden | Out-Null; $outcome.started=$true } catch { $outcome.error=$_.Exception.Message }; return [pscustomobject]$outcome }

if(Test-Path $ConfigFile){ try { $cfg=Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json; if($cfg.unified_api_url){$unifiedApiUrl=[string]$cfg.unified_api_url}; if($cfg.comfyui_url){$comfyUiUrl=[string]$cfg.comfyui_url}; if($cfg.log_file){$logFile=[string]$cfg.log_file}; if($cfg.history_file){$historyFile=[string]$cfg.history_file}; if($cfg.state_file){$stateFile=[string]$cfg.state_file}; if($cfg.webhook_url){$webhookUrl=[string]$cfg.webhook_url}; if($cfg.webhook_format){$webhookFormat=[string]$cfg.webhook_format}; if($cfg.webhook_mention){$webhookMention=[string]$cfg.webhook_mention}; if($null -ne $cfg.notify_on_success){$notifyOnSuccess=To-Bool $cfg.notify_on_success}; if($null -ne $cfg.notify_on_recovery){$notifyOnRecovery=To-Bool $cfg.notify_on_recovery $true}; if($null -ne $cfg.notify_on_partial){$notifyOnPartial=To-Bool $cfg.notify_on_partial $true}; if($null -ne $cfg.notify_on_down){$notifyOnDown=To-Bool $cfg.notify_on_down $true}; if($null -ne $cfg.notify_cooldown_minutes){$notifyCooldownMinutes=[int]$cfg.notify_cooldown_minutes}; if($cfg.notify_state_file){$notifyStateFile=[string]$cfg.notify_state_file}; if($null -ne $cfg.enable_auto_recovery){$enableAutoRecovery=To-Bool $cfg.enable_auto_recovery}; if($null -ne $cfg.recover_after_consecutive_down){$recoverAfterConsecutiveDown=[int]$cfg.recover_after_consecutive_down}; if($null -ne $cfg.recovery_cooldown_sec){$recoveryCooldownSec=[int]$cfg.recovery_cooldown_sec}; if($cfg.recovery_command){$recoveryCommand=[string]$cfg.recovery_command} } catch { Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow } }
if($notifyCooldownMinutes -lt 0){$notifyCooldownMinutes=0}
if($recoverAfterConsecutiveDown -lt 1){$recoverAfterConsecutiveDown=1}
if($recoveryCooldownSec -lt 0){$recoveryCooldownSec=0}
if([string]::IsNullOrWhiteSpace($recoveryCommand)){ $recoveryCommand = "Set-Location '$scriptDir'; `$env:PYTHONIOENCODING='utf-8'; py -3.10 .\unified_api\unified_api_server.py" }

Ensure-ParentDir -Path $logFile; Ensure-ParentDir -Path $historyFile; Ensure-ParentDir -Path $stateFile

$probeJson = & $probeScript -ProbeGenerate -Json -UnifiedApiUrl $unifiedApiUrl -ComfyUiUrl $comfyUiUrl
$probeJson | Set-Content -Path $logFile -Encoding UTF8
$probe = $probeJson | ConvertFrom-Json

$unifiedReady=[bool]$probe.unified_api.ready
$directReady=[bool]$probe.comfyui.ready
$overallOk=($unifiedReady -or $directReady)
$routeCategory = if($unifiedReady){'unified_ready'} elseif($directReady){'direct_fallback'} else {'pipeline_down'}

$now=[datetimeoffset]::Now
$notifyState=Load-NotifyState -Path $notifyStateFile
$pipelineState=Load-PipelineState -Path $stateFile
$pipelineLastCategory=[string]$pipelineState.last_category
$consecutiveDown=0; try{$consecutiveDown=[int]$pipelineState.consecutive_down}catch{$consecutiveDown=0}
$lastRecoveryAt=[string]$pipelineState.last_recovery_at
if($routeCategory -eq 'pipeline_down'){ $consecutiveDown += 1 } else { $consecutiveDown = 0 }

$recoveryAttempt=$null
if($enableAutoRecovery -and $routeCategory -eq 'pipeline_down' -and $consecutiveDown -ge $recoverAfterConsecutiveDown){ $canRecover=$true; if(-not [string]::IsNullOrWhiteSpace($lastRecoveryAt)){ try { $lastDt=[datetimeoffset]::Parse($lastRecoveryAt); if(($now-$lastDt).TotalSeconds -lt $recoveryCooldownSec){$canRecover=$false} } catch { $canRecover=$true } }; if($canRecover){ $recoveryAttempt = Try-RecoverUnifiedApi -UnifiedApiBaseUrl $unifiedApiUrl -CommandText $recoveryCommand; if($recoveryAttempt.started){ $lastRecoveryAt=$now.ToString('o'); Write-Host "[WARN] Auto recovery started for Unified API" -ForegroundColor Yellow } } }

Append-ProbeHistory -Path $historyFile -Entry ([ordered]@{ ts=$now.ToString('o'); category=$routeCategory; unified_ready=$unifiedReady; direct_ready=$directReady; overall_ok=$overallOk; consecutive_down=$consecutiveDown; unified_api_url=$unifiedApiUrl; comfyui_url=$comfyUiUrl; recovery=$recoveryAttempt; probe=$probe })

$msg="category=$routeCategory unifiedReady=$unifiedReady directReady=$directReady consecutiveDown=$consecutiveDown unifiedApi=$unifiedApiUrl comfyUi=$comfyUiUrl"
$lastStatus=[string]$notifyState.last_status
$lastNotifiedAt=$null; if(-not [string]::IsNullOrWhiteSpace([string]$notifyState.last_notified_at)){ try{$lastNotifiedAt=[datetimeoffset]::Parse([string]$notifyState.last_notified_at)}catch{$lastNotifiedAt=$null} }

if(-not $overallOk){ Write-Host "[ALERT] Image pipeline probe failed | $msg" -ForegroundColor Red; $shouldNotifyFailure=$false; if($lastStatus -ne 'failure'){$shouldNotifyFailure=$true} elseif($null -eq $lastNotifiedAt){$shouldNotifyFailure=$true} elseif((($now-$lastNotifiedAt).TotalMinutes) -ge $notifyCooldownMinutes){$shouldNotifyFailure=$true}; if($notifyOnDown -and $shouldNotifyFailure -and -not [string]::IsNullOrWhiteSpace($webhookUrl)){ Send-WebhookNotification -Url $webhookUrl -Format $webhookFormat -Status 'failure' -Title '[Image Pipeline Probe] FAILURE (pipeline_down)' -Body $msg -Mention $webhookMention; Save-NotifyState -Path $notifyStateFile -Status 'failure' -Category $routeCategory -MarkNotified } else { Save-NotifyState -Path $notifyStateFile -Status 'failure' -Category $routeCategory }; Save-PipelineState -Path $stateFile -Category $routeCategory -ConsecutiveDown $consecutiveDown -LastRecoveryAt $lastRecoveryAt; Write-Host "[INFO] Image pipeline probe saved: $logFile" -ForegroundColor Yellow; Write-Host "[INFO] Image pipeline history saved: $historyFile" -ForegroundColor Yellow; exit 1 }

Write-Host "[OK] Image pipeline probe healthy | $msg" -ForegroundColor Green
if($notifyOnPartial -and $routeCategory -eq 'direct_fallback' -and -not [string]::IsNullOrWhiteSpace($webhookUrl) -and [string]$notifyState.last_category -ne 'direct_fallback'){ Send-WebhookNotification -Url $webhookUrl -Format $webhookFormat -Status 'warning' -Title "[Image Pipeline Probe] PARTIAL (direct_fallback)" -Body $msg -Mention $webhookMention }
if($notifyOnRecovery -and -not [string]::IsNullOrWhiteSpace($webhookUrl) -and $routeCategory -eq 'unified_ready' -and $pipelineLastCategory -and $pipelineLastCategory -ne 'unified_ready'){ Send-WebhookNotification -Url $webhookUrl -Format $webhookFormat -Status 'success' -Title "[Image Pipeline Probe] RECOVERED (unified_ready)" -Body $msg -Mention $webhookMention }
if($notifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($webhookUrl) -and $lastStatus -eq 'failure'){ Send-WebhookNotification -Url $webhookUrl -Format $webhookFormat -Status 'success' -Title "[Image Pipeline Probe] SUCCESS ($routeCategory)" -Body $msg -Mention $webhookMention; Save-NotifyState -Path $notifyStateFile -Status 'success' -Category $routeCategory -MarkNotified } else { Save-NotifyState -Path $notifyStateFile -Status 'success' -Category $routeCategory }
Save-PipelineState -Path $stateFile -Category $routeCategory -ConsecutiveDown $consecutiveDown -LastRecoveryAt $lastRecoveryAt
Write-Host "[OK] Image pipeline probe saved: $logFile" -ForegroundColor Green
Write-Host "[OK] Image pipeline history saved: $historyFile" -ForegroundColor Green
exit 0
