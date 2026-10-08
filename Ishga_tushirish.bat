@echo off
chcp 65001 >nul
title CRM
cd /d "%~dp0"
rem Terminal oynasi ko'rinmasligi uchun: oddiy ochilgan bo'lsa, o'zini yashirin rejimda qayta ishga tushiradi
if not "%CRM_HIDDEN%"=="1" (
  start "" wscript.exe "%~dp0tools\windows\crm.vbs"
  exit
)
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  mshta "javascript:alert('Avval Ornatish.bat ni ishga tushiring.');close()"
  exit /b 1
)
set "CHECK=import socket,sys; sys.exit(0 if socket.socket().connect_ex(('127.0.0.1',8000))==0 else 1)"

rem Server ishlamayotgan bo'lsa - fonda ishga tushiramiz va tayyor bo'lishini kutamiz
"%PY%" -c "%CHECK%"
if %errorlevel%==0 goto open
start "" /b cmd /c "tools\windows\server.bat"
for /l %%i in (1,1,40) do (
  timeout /t 1 /nobreak >nul
  "%PY%" -c "%CHECK%" && goto open
)
rem Yashirin rejimda xabar oynasi orqali bildiramiz
mshta "javascript:alert('CRM serveri ishga tushmadi. Sababi: logs\\server.log');close()"
exit /b 1

:open
call tools\windows\open_app.bat http://localhost:8000/
exit /b 0
