@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo   Stopping TweetSupport AI Support Agent Stack...
echo ==========================================================
echo.

docker compose down

echo.
echo All containers stopped successfully.
pause