' ==========================================================
' ManaOS Silent Startup Script (VBScript)
' Launches ManaOS services completely in background
' Window Style: 0 = Hidden, False = Don't wait for completion
' ==========================================================

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strBatchFile = objFSO.BuildPath(strScriptDir, "start_manaos_autostart.bat")

' Create logs directory if needed
strLogsDir = objFSO.BuildPath(strScriptDir, "logs")
If Not objFSO.FolderExists(strLogsDir) Then
    objFSO.CreateFolder(strLogsDir)
End If

' Log the startup time
Set objLogFile = objFSO.OpenTextFile(objFSO.BuildPath(strLogsDir, "startup.log"), 8, True)
objLogFile.WriteLine "[" & Now & "] VBScript launcher starting batch file: " & strBatchFile
objLogFile.Close()

' Run the batch file in hidden mode
' Parameters: (strCommand, intWindowStyle, bWaitOnReturn)
' intWindowStyle: 0 = Hidden (most important for background execution)
' bWaitOnReturn: False = Don't wait (async execution)
objShell.Run strBatchFile, 0, False

' Exit immediately without any output
WScript.Quit

