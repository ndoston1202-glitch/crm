@echo off
chcp 65001 >nul
rem CRM serverini to'xtatadi (masalan, kompyuterni o'chirishdan oldin shart emas, faqat kerak bo'lsa)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*manage.py runserver*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | Where-Object { $_.CommandLine -like '*server.bat*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo CRM serveri to'xtatildi.
timeout /t 2 >nul
