@echo off
rem CRM serveri (fonda ishlaydi). Dastur ichidan yangilanganda 3-kod bilan to'xtaydi va qayta ishga tushadi.
cd /d "%~dp0..\.."
if not exist logs mkdir logs
set CRM_LAUNCHER=1
:loop
echo [%date% %time%] Server ishga tushdi >> logs\server.log
".venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000 --noreload >> logs\server.log 2>&1
if %errorlevel%==3 goto loop
echo [%date% %time%] Server to'xtadi (kod %errorlevel%) >> logs\server.log
