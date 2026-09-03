@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1"
if errorlevel 1 (
  echo.
  echo Setup or startup failed. Review the message above.
  pause
  exit /b 1
)

