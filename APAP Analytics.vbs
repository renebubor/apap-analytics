
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = projectDir & "\.venv\Scripts\pythonw.exe"
appFile = projectDir & "\app_launcher.py"

command = """" & pythonExe & """ """ & appFile & """"

shell.CurrentDirectory = projectDir
shell.Run command, 1, False
