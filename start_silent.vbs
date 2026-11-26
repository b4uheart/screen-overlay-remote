Dim WshShell, FSO, scriptDir, cmd
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' Run pythonw completely hidden (0 = hide window)
cmd = "pythonw.exe """ & scriptDir & "\overlay.py"""
WshShell.Run cmd, 0, False

WshShell.Popup "Headless Screen Overlay Daemon Started!" & vbCrLf & vbCrLf & _
               "• 0 GUI / 0 Pixels on PC (100% Headless)" & vbCrLf & _
               "• Mobile Display: http://<PC-IP>:5050/display" & vbCrLf & _
               "• Controller:     http://<PC-IP>:5050" & vbCrLf & _
               "• Stop: Double-click stop_overlay.bat", 4, "Overlay Daemon Active", 64
