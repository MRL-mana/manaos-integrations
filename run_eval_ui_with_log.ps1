# 評価UIを起動し、標準出力・エラーをログに記録
$logPath = Join-Path $PSScriptRoot "eval_ui_startup.log"
$scriptPath = Join-Path $PSScriptRoot "start_evaluation_ui_port9601.py"
Set-Location $PSScriptRoot
"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $logPath -Encoding utf8
python -u $scriptPath 2>&1 | Tee-Object -FilePath $logPath -Append -Encoding utf8
