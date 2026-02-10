' ManaOS Silent Startup via PowerShell
' More robust than batch file for complete window hiding

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get script directory
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Build PowerShell command using Start-Job (completely hidden)
strPSCommand = "Start-Job -ScriptBlock { Set-Location '" & strScriptDir & "'; & $env:VENV\Scripts\python.exe start_vscode_cursor_services.py >> logs\autostart.log 2>&1 } -WindowStyle Hidden"

' Alternative: Use Windows API call for best control, or use Start-Process -WindowStyle Hidden
' Run PowerShell with hidden window
objShell.Run "powershell.exe -NoProfile -WindowStyle Hidden -Command """ & strPSCommand & """", 0, False

WScript.Quit
