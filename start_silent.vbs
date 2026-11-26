Dim WshShell, FSO, scriptDir, cmd
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Get the directory of this VBS script
scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' Run pythonw completely hidden (0 = hide window)
cmd = "pythonw.exe """ & scriptDir & "\overlay.py"""
WshShell.Run cmd, 0, False

' Optional 3-second notification that closes itself automatically
WshShell.Popup "Overlay is running silently in the background!" & vbCrLf & vbCrLf & _
               "• Taskbar: Clean (No Icon)" & vbCrLf & _
               "• Control: Use your phone or press Ctrl+Shift+X" & vbCrLf & _
               "• Stop: Double-click stop_overlay.bat", 3, "Screen Overlay Started", 64
