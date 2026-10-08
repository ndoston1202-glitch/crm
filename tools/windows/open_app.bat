@echo off
rem CRM ni alohida ilova oynasida ochadi (manzil satri va tablarsiz).
rem Foydalanish: open_app.bat http://localhost:8000/
set "URL=%~1"
if "%URL%"=="" set "URL=http://localhost:8000/"
set "PROFILE=%LOCALAPPDATA%\CRM\app-profile"

set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if exist "%BROWSER%" goto open
set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if exist "%BROWSER%" goto open
set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if exist "%BROWSER%" goto open
set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%BROWSER%" goto open
set "BROWSER=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if exist "%BROWSER%" goto open

rem Edge ham, Chrome ham topilmadi - oddiy brauzerda ochamiz
start "" "%URL%"
exit /b 0

:open
start "" "%BROWSER%" --app="%URL%" --user-data-dir="%PROFILE%" --window-size=1400,900 --no-first-run --no-default-browser-check
exit /b 0
