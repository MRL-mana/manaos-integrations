$interval = 120
$monitor_log = "C:\Users\mana4\Desktop\manaos_integrations\v1_1_2_monitor.log"
$ck2500_path = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_2\checkpoint-2500"
$training_done = $false

while(-not $training_done) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $trainProc = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*train_castle_ex_lora.py*' }
    $train_alive = $null -ne $trainProc
    $ck2500_exists = Test-Path $ck2500_path

    "[$timestamp] train_alive=$train_alive ck2500=$ck2500_exists" | Add-Content $monitor_log

    if($ck2500_exists -or -not $train_alive) {
        "[$timestamp] [TRIGGER_DETECTED]" | Add-Content $monitor_log
        $training_done = $true
    } else {
        Start-Sleep -Seconds $interval
    }
}
