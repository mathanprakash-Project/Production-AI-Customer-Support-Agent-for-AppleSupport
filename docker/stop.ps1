# PowerShell script to stop the TweetSupport Docker environment
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Stopping all TweetSupport containers..." -ForegroundColor Yellow
docker compose down
Write-Host "All containers stopped successfully." -ForegroundColor Green

