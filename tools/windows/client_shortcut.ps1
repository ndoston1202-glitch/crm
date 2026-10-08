param([string]$Url)
# Xodim kompyuterida ish stoliga CRM belgisi (alohida ilova oynasi)
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$iconDir = Join-Path $env:LOCALAPPDATA "CRM"
New-Item -ItemType Directory -Force -Path $iconDir | Out-Null
Copy-Item (Join-Path $Root "static\img\crm.ico") (Join-Path $iconDir "crm.ico") -Force
Copy-Item (Join-Path $Root "tools\windows\open_app.bat") (Join-Path $iconDir "open_app.bat") -Force
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "CRM.lnk"))
$lnk.TargetPath = Join-Path $iconDir "open_app.bat"
$lnk.Arguments = $Url
$lnk.IconLocation = (Join-Path $iconDir "crm.ico") + ",0"
$lnk.WindowStyle = 7
$lnk.Description = "CRM"
$lnk.Save()
Write-Host "Tayyor! Ish stolidagi CRM belgisini bosing ($Url)" -ForegroundColor Green
