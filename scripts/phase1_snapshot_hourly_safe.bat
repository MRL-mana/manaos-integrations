@echo off
setlocal
cd /d "C:\Users\mana4\Desktop\manaos_integrations"


set "dt=%date:~0,4%-%date:~5,2%-%date:~8,2%"
set "hh=%time:~0,2%"
set "hh=%hh: =0%"

start /min "" "C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe" "C:\Users\mana4\Desktop\manaos_integrations\phase1_metrics_snapshot.py" "snapshots\%dt%\%hh%.json" "C:\Users\mana4\Desktop\manaos_integrations\phase1_metrics_snapshot_baseline.json"
endlocal

