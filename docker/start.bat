@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo   Starting TweetSupport AI Support Agent (Full Docker Stack)
echo ==========================================================
echo.
echo Starting Database, Ollama, Backend, and Frontend...
echo.

docker compose up -d --build

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start Docker Compose containers.
    echo Please make sure Docker Desktop is running.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Containers started successfully!
echo Waiting for services to initialize...
timeout /t 5 /nobreak >nul

echo.
echo ==========================================================
echo   Services are running:
echo   - Frontend Workspace: http://localhost:5173
echo   - Backend API Docs:   http://localhost:8000/docs
echo   - Health Check:       http://localhost:8000/api/v1/health
echo   - PostgreSQL (pgvector): localhost:5433
echo.
echo   Default Credentials:
echo   - Agent: agent@tweetsupport.local / agent123
echo   - Admin: admin@tweetsupport.local / admin123
echo ==========================================================
echo.
pause

