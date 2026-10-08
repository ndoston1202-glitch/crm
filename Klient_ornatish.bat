@echo off
chcp 65001 >nul
title CRM - xodim kompyuteriga o'rnatish
cd /d "%~dp0"
rem Operator kompyuterlari uchun: Python kerak emas, faqat ish stolida CRM belgisi yaratiladi.
echo CRM server kompyuterining manzilini kiriting.
echo U CRM dagi "Telefon ilovasi" sahifasida ko'rsatilgan, masalan: 192.168.1.10
set /p SERVER=Server manzili: 
if "%SERVER%"=="" exit /b 1
echo %SERVER% | find ":" >nul || set "SERVER=%SERVER%:8000"
echo %SERVER% | find "http" >nul || set "SERVER=http://%SERVER%"
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\windows\client_shortcut.ps1" -Url "%SERVER%/"
pause
