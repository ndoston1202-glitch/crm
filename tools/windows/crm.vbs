' CRM ni qora oynasiz ishga tushiradi (ish stolidagi CRM belgisi shu faylni ochadi)
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName)))
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = root
sh.Environment("PROCESS")("CRM_HIDDEN") = "1"
sh.Run """" & root & "\Ishga_tushirish.bat""", 0, False
