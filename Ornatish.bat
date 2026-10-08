@echo off
chcp 65001 >nul
title CRM - o'rnatish
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\windows\install.ps1"
echo.
pause
