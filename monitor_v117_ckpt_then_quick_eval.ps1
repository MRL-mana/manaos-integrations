param(
    [string]$OutDir = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_7_patch",
    [int]$CheckpointStep = 300,
    [int]$PollSec = 60,
    [string]$BaseModel = "D:\castle_ex_training\castle_ex_v1_1",
    [string]$EvalData = "castle_ex_dataset_layer2_lora_v1_1_6_audit100.jsonl"
)

$ErrorActionPreference = "Stop"
$root       = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir     = Join-Path $root "logs"
$reportsDir = Join-Path $root "Reports"
if (-not (Test-Path $logDir))     { New-Item -ItemType Directory -Force $logDir     | Out-Null }
if (-not (Test-Path $reportsDir)) { New-Item -ItemType Directory -Force $reportsDir | Out-Null }

$timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$monitorLog = Join-Path $logDir "monitor_v117_ck${CheckpointStep}_$timestamp.log"
$stdoutLog  = Join-Path $logDir "layer2_quick_eval_v117_ck${CheckpointStep}_$timestamp.stdout.log"
$stderrLog  = Join-Path $logDir "layer2_quick_eval_v117_ck${CheckpointStep}_$timestamp.stderr.log"

$ckPath = Join-Path $OutDir "checkpoint-$CheckpointStep"
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] watch start: $ckPath" | Add-Content $monitorLog -Encoding UTF8

while (-not (Test-Path $ckPath)) {
    Start-Sleep -Seconds $PollSec
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] waiting for checkpoint-$CheckpointStep ..." | Add-Content $monitorLog -Encoding UTF8
}
Start-Sleep -Seconds 20
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] checkpoint found: $ckPath" | Add-Content $monitorLog -Encoding UTF8

$quickEvalScript = Join-Path $root "scripts\run\run_layer2_quick_eval.py"
$evalDataPath    = if ([System.IO.Path]::IsPathRooted($EvalData)) { $EvalData } else { Join-Path $root $EvalData }

$evalArgs = @(
    "-3.10", "-u", $quickEvalScript,
    "--base-model",      $BaseModel,
    "--output-dir",      $OutDir,
    "--checkpoint-step", "$CheckpointStep",
    "--eval-data",       $evalDataPath,
    "--device-map",      "cuda:0",
    "--reports-dir",     "Reports",
    "--max-new-tokens",  "64"
)
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] starting quick-eval checkpoint=$CheckpointStep" | Add-Content $monitorLog -Encoding UTF8

$evalProc = Start-Process -FilePath "py.exe" -ArgumentList $evalArgs `
    -WorkingDirectory $root `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError  $stderrLog `
    -PassThru -Wait
if ($evalProc.ExitCode -ne 0) { throw "quick eval failed exit=$($evalProc.ExitCode)" }

$latest = Get-ChildItem $reportsDir -Filter "castle_ex_layer2_quick_eval_checkpoint-$CheckpointStep*.json" |
    Sort-Object LastWriteTime -Desc | Select-Object -First 1
if (-not $latest) { throw "eval json not found in $reportsDir" }

$evalJson = Get-Content $latest.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
$details  = @($evalJson.details)
$errors   = $details | Where-Object { $_.ok -eq $false }
$haiToken = ([string][char]0x306f) + ([string][char]0x3044)
$containsHai = 0; $containsRepeat = 0
foreach ($row in $errors) {
    $pred = [string]$row.pred
    if ($pred.Contains($haiToken)) { $containsHai++ }
    $parts = @($pred -split "\s+" | Where-Object { $_ -and $_.Length -ge 2 })
    if ($parts.Count -gt 1) {
        $grp = $parts | Group-Object | Sort-Object Count -Desc | Select-Object -First 1
        if ($grp -and $grp.Count -ge 2) { $containsRepeat++ }
    }
}
$acc    = [double]$evalJson.summary.acc
$passed = (($acc -ge 0.75) -and ($containsHai -le 10) -and ($containsRepeat -le 5))

$gate = [ordered]@{
    version                = "v1.1.7"
    checkpoint             = $CheckpointStep
    eval_json              = $latest.FullName
    acc                    = $acc
    contains_hai           = $containsHai
    contains_repeat_phrase = $containsRepeat
    passed                 = $passed
    generated_at           = (Get-Date).ToString("s")
}
$gatePath = Join-Path $reportsDir "gate_v117_ck${CheckpointStep}_$timestamp.json"
$gate | ConvertTo-Json -Depth 5 | Set-Content $gatePath -Encoding UTF8

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] gate=$gatePath acc=$acc passed=$passed" | Add-Content $monitorLog -Encoding UTF8
Write-Host "[gate_v117] acc=$acc contains_hai=$containsHai contains_repeat=$containsRepeat passed=$passed"
Write-Host "[gate_v117] file=$gatePath"

if ($passed) { exit 0 } else { exit 2 }
