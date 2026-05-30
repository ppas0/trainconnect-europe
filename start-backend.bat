@echo off
echo.
echo  TrainConnect Europe v1.7 - Backend starten
echo  ============================================
echo.
set PATH=C:\Program Files\nodejs;%PATH%
cd /d "%~dp0backend"
node server.js
pause
