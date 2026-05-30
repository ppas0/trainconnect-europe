@echo off
echo.
echo  TrainConnect Europe v1.7 - Frontend starten
echo  =============================================
echo  Warte ca. 30-60 Sekunden bis der Build fertig ist...
echo  Dann oeffnet sich http://localhost:3000 automatisch im Browser.
echo.
set PATH=C:\Program Files\nodejs;%PATH%
set REACT_APP_BACKEND_URL=http://localhost:5000
set BROWSER=chrome
set CI=false
cd /d "%~dp0frontend"
node_modules\.bin\craco.cmd start
pause
