' ダブルクリックでバッチを実行し、ウィンドウを閉じないようにする
Set fso = CreateObject("Scripting.FileSystemObject")
batDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(batDir, "cursor_chat_history_開く.bat")
CreateObject("WScript.Shell").Run "cmd /k cd /d """ & batDir & """ && """ & batPath & """", 1, True
