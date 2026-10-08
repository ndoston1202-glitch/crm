@echo off
chcp 65001 >nul
title CRM server
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Avval Ornatish.bat ni ishga tushiring.
  pause
  exit /b 1
)
set PORT=8000

rem Server allaqachon ishlayotgan bo'lsa, faqat brauzerni ochamiz
"%PY%" -c "import socket,sys; sys.exit(0 if socket.socket().connect_ex(('127.0.0.1',%PORT%))==0 else 1)"
if %errorlevel%==0 (
  start "" http://localhost:%PORT%/
  exit /b 0
)

start "" /b cmd /c "timeout /t 4 >nul & start http://localhost:%PORT%/"
set CRM_LAUNCHER=1
:loop
"%PY%" manage.py runserver 0.0.0.0:%PORT% --noreload
rem Chiqish kodi 3 = dastur ichidan yangilandi, qayta ishga tushiramiz
if %errorlevel%==3 (
  echo Yangilanish o'rnatildi, qayta ishga tushirilmoqda...
  goto loop
)
echo Server to'xtadi.
pause
