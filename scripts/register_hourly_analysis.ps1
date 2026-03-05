# ManaOS_HourlyAnalysis TaskScheduler 登録スクリプト
# 管理者として実行してください: 右クリック → 管理者として実行
# または VS Code タスク「ManaOS: register hourly analysis」から実行

$TaskName = "ManaOS_HourlyAnalysis"
$Python   = "C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe"
$Script   = "C:\Users\mana4\Desktop\manaos_integrations\scripts\misc\manaos_daily_report.py"
$WorkDir  = "C:\Users\mana4\Desktop\manaos_integrations"

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT1H</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2026-03-05T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions>
    <Exec>
      <Command>$Python</Command>
      <Arguments>$Script</Arguments>
      <WorkingDirectory>$WorkDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\ManaOS_HourlyAnalysis.xml"
$xml | Out-File -FilePath $xmlPath -Encoding Unicode

$result = schtasks /Create /TN $TaskName /XML $xmlPath /F 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] $TaskName を登録しました（1時間ごと）" -ForegroundColor Green
} else {
    Write-Host "[ERROR] 登録失敗: $result" -ForegroundColor Red
    Write-Host "ヒント: 管理者として PowerShell を起動して再実行してください" -ForegroundColor Yellow
}

Remove-Item $xmlPath -ErrorAction SilentlyContinue
