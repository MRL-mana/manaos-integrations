@echo off
cd /d "C:\Users\mana4\Desktop\manaos_integrations"
"C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe" "C:\Users\mana4\Desktop\manaos_integrations\phase1_metrics_snapshot.py" "snapshots\%date:~0,4%-%date:~5,2%-%date:~8,2%\%time:~0,2%.json" "C:\Users\mana4\Desktop\manaos_integrations\phase1_metrics_snapshot_baseline.json"

