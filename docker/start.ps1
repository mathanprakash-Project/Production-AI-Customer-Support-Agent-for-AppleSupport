# PowerShell script to start the TweetSupport full-stack Docker environment
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Starting TweetSupport AI Support Agent (Full Docker Stack)    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Verify docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Database, Ollama, Backend, and Frontend containers..." -ForegroundColor Yellow
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker compose failed to start." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Waiting for services to be ready..." -ForegroundColor Gray
Start-Sleep -Seconds 4

# Check backend health
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 5
    Write-Host "Backend Status: " -NoNewline
    Write-Host "HEALTHY" -ForegroundColor Green
} catch {
    Write-Host "Backend is still initializing. Check 'docker compose logs -f' if needed." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  Application is ready:" -ForegroundColor Green
Write-Host "  - Frontend Workspace: http://localhost:5173" -ForegroundColor White
Write-Host "  - Backend API Docs:   http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Health Endpoint:    http://localhost:8000/api/v1/health" -ForegroundColor White
Write-Host "  - PostgreSQL:         localhost:5433" -ForegroundColor White
Write-Host ""
Write-Host "  Default Login Credentials:" -ForegroundColor Cyan
Write-Host "  - Agent: agent@tweetsupport.local / agent123" -ForegroundColor White
Write-Host "  - Admin: admin@tweetsupport.local / admin123" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green

