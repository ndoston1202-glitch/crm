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
$LocalFfmpeg = Join-Path $Root "tools\ffmpeg\bin\ffmpeg.exe"
if (-not (Has "ffmpeg") -and -not (Test-Path $LocalFfmpeg)) {
    try { WingetInstall "Gyan.FFmpeg.Essentials" "FFmpeg" } catch { }
    if (-not (Has "ffmpeg")) {
        # winget ishlamadi (masalan "Access is denied") - CRM papkasining o'ziga yuklab olamiz
        Write-Host "FFmpeg to'g'ridan-to'g'ri yuklab olinmoqda (~30 MB)..."
        try {
            $zip = Join-Path $env:TEMP "crm-ffmpeg.zip"
            $tmp = Join-Path $env:TEMP "crm-ffmpeg"
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $ProgressPreference = "SilentlyContinue"
            Invoke-WebRequest "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $zip -UseBasicParsing
            if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
            Expand-Archive $zip -DestinationPath $tmp -Force
            $exe = Get-ChildItem $tmp -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
            New-Item -ItemType Directory -Force -Path (Split-Path $LocalFfmpeg) | Out-Null
            Copy-Item $exe.FullName $LocalFfmpeg -Force
            Remove-Item $zip, $tmp -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "FFmpeg o'rnatildi: $LocalFfmpeg" -ForegroundColor Green
        } catch {
            Write-Warning "FFmpeg o'rnatilmadi - ovoz yozuvlari MP3 ga aylantirilmaydi. Internetni tekshirib Ornatish.bat ni qayta ishga tushiring."
        }
    }
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
    # Uzoq yuklash paytida bosilgan tugmalar parol bo'lib ketmasligi uchun klaviatura buferini tozalaymiz
    try { while ([Console]::KeyAvailable) { [void][Console]::ReadKey($true) } } catch { }
    while ($true) {
        $p1 = Read-Host "admin uchun parol kiriting (kamida 6 belgi)" -AsSecureString
        $p2 = Read-Host "Parolni qayta kiriting" -AsSecureString
        $plain1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p1))
        $plain2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p2))
        if ($plain1.Length -lt 6) { Write-Warning "Parol juda qisqa, qaytadan kiriting."; continue }
        if ($plain1 -ne $plain2) { Write-Warning "Parollar mos kelmadi, qaytadan kiriting."; continue }
        break
    }
    # Parol buyruq qatorida ko'rinmasligi uchun muhit o'zgaruvchisi orqali beriladi
    $env:CRM_ADMIN_PASSWORD = $plain1
    & $VPy manage.py ensure_admin --username admin
    Remove-Item Env:CRM_ADMIN_PASSWORD
    if ($LASTEXITCODE -ne 0) { Write-Warning "Administrator yaratilmadi. Qo'lda: .venv\Scripts\python.exe manage.py ensure_admin --password PAROL" }
} else { Write-Host "Administrator allaqachon mavjud." }

Step "Ish stolida CRM yorlig'i"
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $desktop "CRM.lnk"))
$lnk.TargetPath = Join-Path $env:WINDIR "System32\wscript.exe"
$lnk.Arguments = '"' + (Join-Path $Root "tools\windows\crm.vbs") + '"'
$lnk.WorkingDirectory = "$Root"
$lnk.IconLocation = (Join-Path $Root "static\img\crm.ico") + ",0"
$lnk.WindowStyle = 7
$lnk.Description = "CRM ni ishga tushirish"
$lnk.Save()

Write-Host ""
Write-Host "Tayyor! Ish stolidagi CRM belgisini bosing." -ForegroundColor Green
Write-Host "Login: admin"
