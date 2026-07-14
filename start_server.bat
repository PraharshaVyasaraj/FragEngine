@echo off
REM FragEngine V0.15 — Server Launcher
REM Activates the isolated venv then starts the Flask server

echo.
echo  ================================================
echo   FragEngine ^| Server Starting...
echo   Venv: C:\FragEngine\venv
echo  ================================================
echo.

call C:\FragEngine\venv\Scripts\activate.bat

python C:\FragEngine\server.py

pause
