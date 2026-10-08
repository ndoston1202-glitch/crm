# CRM o'rnatuvchisi (Windows). Ornatish.bat orqali ishga tushiriladi.
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

function Step($text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }
function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function WingetInstall($id, $name) {
    if (-not (Has "winget")) { throw "$name topilmadi va winget yo'q. $name ni qo'lda o'rnating va qayta urinib ko'ring." }
    Write-Host "$name o'rnatilmoqda..."
    winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements | Out-Host
    Refresh-Path
}

Step "Python tekshirilmoqda"
$Py = $null
if (Has "py") { $Py = "py" } elseif (Has "python") { $Py = "python" }
if (-not $Py) { WingetInstall "Python.Python.3.12" "Python"; $Py = if (Has "py") { "py" } else { "python" } }
& $Py --version

Step "Git tekshirilmoqda (dastur ichidan yangilash uchun)"
if (-not (Has "git")) { WingetInstall "Git.Git" "Git" }

Step "Yangilanishlar manbasi (git)"
$RepoUrl = "https://github.com/ndoston1202-glitch/crm.git"
$Branch = "main"
if (-not (Test-Path ".git")) {
    # ZIP orqali yuklab olingan bo'lsa - git ni sozlaymiz, shunda dastur ichidan yangilash ishlaydi
    git init -q -b $Branch
    git remote add origin $RepoUrl
    git fetch -q origin $Branch
    if ($LASTEXITCODE -eq 0) {
        git reset -q --mixed "origin/$Branch"
        git branch -q --set-upstream-to="origin/$Branch"
    } else {
        Write-Warning "GitHub ga ulanib bo'lmadi (repo yopiq bo'lsa, git login qiling). Yangilash keyinroq sozlanadi."
    }
}

Step "FFmpeg tekshirilmoqda (ovoz yozuvlarini MP3 ga aylantirish uchun)"
if (-not (Has "ffmpeg")) {
    try { WingetInstall "Gyan.FFmpeg" "FFmpeg" } catch { Write-Warning "FFmpeg o'rnatilmadi - yozuvlar MP3 ga aylantirilmaydi. Keyinroq qo'lda o'rnating." }
}

Step "Virtual muhit va kutubxonalar"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $Py -m venv .venv }
$VPy = Join-Path $Root ".venv\Scripts\python.exe"
& $VPy -m pip install --upgrade pip -q
& $VPy -m pip install -r requirements.txt -q

Step "Sozlamalar fayli (.env)"
if (-not (Test-Path ".env")) {
    $secret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 50 | ForEach-Object { [char]$_ })
    @(
        "SECRET_KEY=$secret",
        "DEBUG=1",
        "ALLOWED_HOSTS=*",
        "# Asterisk (IP-telefoniya) - kerak bo'lsa to'ldiring, batafsil: docs\asterisk.md",
        "ASTERISK_AMI_HOST=",
        "ASTERISK_AMI_SECRET=",
        "ASTERISK_WEBHOOK_TOKEN="
    ) | Set-Content -Encoding UTF8 ".env"
}

Step "Ma'lumotlar bazasi"
& $VPy manage.py migrate --noinput
& $VPy tools\compile_translations.py

Step "Administrator"
$hasAdmin = & $VPy manage.py shell -c "from accounts.models import User; print(User.objects.filter(is_superuser=True).exists())"
if ($hasAdmin -notmatch "True") {
    $pwd1 = Read-Host "admin foydalanuvchisi uchun parol kiriting"
    & $VPy manage.py ensure_admin --username admin --password $pwd1
} else { Write-Host "Administrator allaqachon mavjud." }

Step "Ish stolida CRM yorlig'i"
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $desktop "CRM.lnk"))
$lnk.TargetPath = Join-Path $Root "Ishga_tushirish.bat"
$lnk.WorkingDirectory = "$Root"
$lnk.IconLocation = (Join-Path $Root "static\img\crm.ico") + ",0"
$lnk.WindowStyle = 7
$lnk.Description = "CRM ni ishga tushirish"
$lnk.Save()

Write-Host ""
Write-Host "Tayyor! Ish stolidagi CRM belgisini bosing." -ForegroundColor Green
Write-Host "Login: admin"
